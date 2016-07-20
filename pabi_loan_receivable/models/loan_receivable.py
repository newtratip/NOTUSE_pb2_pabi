# -*- coding: utf-8 -*-

from openerp import models, api, fields, _
from openerp.exceptions import ValidationError, Warning as UserError


class LoanBankMOU(models.Model):
    _name = "loan.bank.mou"
    _description = "MOU between Bank and NSTDA"

    name = fields.Char(
        string='MOU Number',
        required=True,
        copy=False,
    )
    bank_id = fields.Many2one(
        'res.partner.bank',
        string='Bank',
        required=True,
    )
    max_installment = fields.Integer(
        string='Max Installment',
        required=True,
        default=1,
    )
    loan_ratio = fields.Float(
        string='Loan Ratio (NSTDA/Bank)',
        help="Ratio of loan between NSTDA and Bank. For example, 2:1 = 2 "
        "means NSTDA will load 2 part and Bank will load 1 part",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Loan Product',
        required=True,
    )
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'MOU Number must be unique!'),
    ]


class LoanCustomerAgreement(models.Model):
    _name = "loan.customer.agreement"
    _inherit = ['mail.thread']
    _description = "Loan Agreement between Bank and Customer, CC NSTDA"

    name = fields.Char(
        string='Loan Agreement Number',
        required=True,
        copy=False,
    )
    mou_id = fields.Many2one(
        'loan.bank.mou',
        string='MOU',
        required=True,
        ondelete='restrict',
    )
    bank_id = fields.Many2one(
        'res.partner.bank',
        related="mou_id.bank_id",
        string='Bank',
        readonly=True,
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
    )
    amount_loan_total = fields.Float(
        string='Total Loan Amount from Bank',
        default=0.0,
    )
    amount_receivable = fields.Float(
        string='Loan Amount from NSTDA',
        default=0.0,
    )
    installment = fields.Integer(
        string='Number of Installment',
        default=1,
    )
    date_begin = fields.Date(
        string='Begin Date',
        required=True,
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
    )
    monthly_due_type = fields.Selection(
        [('first', 'First day of month'),
         ('last', 'Last day of month'),
         ('specific', 'Specific date (1-28)')],
        string='Payment Due Type',
        default='last',
        required=True,
    )
    date_specified = fields.Integer(
        string='Specify Date',
        default=1,
    )
    supplier_invoice_id = fields.Many2one(
        'account.invoice',
        string='Bank Invoice',
        readonly=True,
        copy=False,
    )
    sale_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        readonly=True,
    )
    invoice_plan_ids = fields.One2many(
        'sale.invoice.plan',
        related='sale_id.invoice_plan_ids',
        string='Installment Plan',
        readonly=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('sign', 'Document Signed'),
         ('bank_invoice', 'Bank Invoiced'),
         ('bank_paid', 'Bank Paid'),
         ('open', 'Installment Open'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],
        string='Status',
        readonly=True,
        default='draft',
        compute='_compute_state',
        store=True,
    )
    # Fields for state
    signed = fields.Boolean(
        string='Signed',
        default=False,
    )
    cancelled = fields.Boolean(
        string='Cancelled',
        default=False,
    )

    @api.multi
    @api.depends('signed',
                 'supplier_invoice_id',
                 'supplier_invoice_id.state',
                 'sale_id',
                 'sale_id.state',)
    def _compute_state(self):
        for rec in self:
            state = 'draft'
            if rec.cancelled:
                state = 'cancel'
            if rec.signed:
                state = 'sign'
            if rec.supplier_invoice_id and \
                    rec.supplier_invoice_id.state not in ('cancel', 'paid',):
                state = 'bank_invoice'
            if rec.supplier_invoice_id and \
                    rec.supplier_invoice_id.state == 'paid':
                state = 'bank_paid'
            if rec.sale_id:
                state = 'open'
            if rec.sale_id and \
                    rec.sale_id.state == 'done':
                state = 'done'
            rec.state = state

    @api.one
    @api.constrains('monthly_due_type', 'date_specified')
    def _check_date_specified(self):
        if self.monthly_due_type == 'specific' and \
                (self.date_specified < 1 or self.date_specified > 28):
            raise Warning(_('Specified date must be between 1 - 28'))

    @api.multi
    def action_sign(self):
        self.write({'signed': True,
                    'cancelled': False})

    @api.multi
    def action_cancel(self):
        self.write({'signed': False,
                    'cancelled': True})

    @api.multi
    def action_cancel_draft(self):
        self.write({'cancelled': False})

    @api.multi
    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise ValidationError(
                    _('Cannot delete Loan Agreement which is not '
                      'in state draft or cancelled!'))
        return super(LoanCustomerAgreement, self).unlink()

    @api.multi
    def create_bank_invoice(self, date_invoice):
        for loan in self:
            invoice = loan._create_bank_supplier_invoice_for_loan(date_invoice)
            loan.write({'supplier_invoice_id': invoice.id,
                        'state': 'bank_invoice'})
        return True

    @api.multi
    def _create_bank_supplier_invoice_for_loan(self, date_invoice=False):
        self.ensure_one()
        inv_lines = []
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']
        loan = self
        invoice_vals = self._prepare_inv_header(loan,
                                                date_invoice)
        inv_line_data = self._prepare_inv_line(loan,
                                               invoice_vals['fiscal_position'])
        inv_line = InvoiceLine.create(inv_line_data)
        inv_lines.append(inv_line.id)
        invoice_vals.update({'invoice_line': [(6, 0, inv_lines)]})
        # Create Invoice
        invoice = Invoice.create(invoice_vals)
        # Set due date
        res = invoice.onchange_payment_term_date_invoice(
            invoice.payment_term.id, invoice.date_invoice)
        invoice.date_due = res['value']['date_due']
        invoice.button_compute(set_total=True)
        return invoice

    @api.model
    def _prepare_inv_header(self, loan, date_invoice):
        Invoice = self.env['account.invoice']
        Journal = self.env['account.journal']
        # Journal
        company_id = self._context.get('company_id',
                                       self.env.user.company_id.id)
        partner_id = loan.bank_id.partner_id.id
        currency_id = self.env.user.company_id.currency_id.id
        journal = Journal.search([('type', '=', 'purchase'),
                                  ('company_id', '=', company_id)],
                                 limit=1)
        if not journal:
            raise UserError(
                _("No purchase journal found. Please make sure you "
                  "have a journal with type 'purchase' configured."))
        journal_id = journal[0].id

        res = Invoice.onchange_partner_id(
            'in_invoice', partner_id, date_invoice, payment_term=False,
            partner_bank_id=False, company_id=company_id)['value']

        return {
            'origin': loan.name,
            'comment': False,
            'date_invoice': date_invoice,
            'user_id': self.env.user.id,
            'partner_id': partner_id,
            'account_id': res.get('account_id', False),
            'payment_term': res.get('payment_term', False),
            'fiscal_position': res.get('fiscal_position', False),
            'type': 'in_invoice',
            'company_id': company_id,
            'currency_id': currency_id,
            'journal_id': journal_id,
            'loan_agreement_id': loan.id,
        }

    @api.model
    def _prepare_inv_line(self, loan, fposition_id):
        InvoiceLine = self.env['account.invoice.line']
        res = InvoiceLine.product_id_change(loan.mou_id.product_id.id, False,
                                            qty=1, name='', type='in_invoice',
                                            partner_id=loan.partner_id.id,
                                            fposition_id=fposition_id)['value']
        return {
            'product_id': loan.mou_id.product_id.id,
            'name': res.get('name', False),
            'account_id': res.get('account_id', False),
            'price_unit': loan.amount_receivable,
            'quantity': 1.0,
            'uos_id': res.get('uos_id', False),
        }