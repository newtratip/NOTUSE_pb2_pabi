# -*- coding: utf-8 -*-
import logging
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HRExpense(models.Model):
    _inherit = 'hr.expense.expense'

    @api.multi
    def action_accept_to_paid(self):
        # Start with confirm status
        expenses = self.filtered(lambda l: l.is_employee_advance)
        print expenses
        # for expense in expenses:
        for expense in expenses:
            try:
                # Accept
                if expense.state == 'confirm':
                    expense.signal_workflow('validate')
                # Create Invoice
                if expense.state == 'accepted':
                    vals = {'date_invoice': fields.Date.context_today(self),
                            'pay_to': 'employee'}
                    self.env['expense.create.supplier.invoice'].create(vals).\
                        with_context({'active_id': expense.id}).\
                        action_create_supplier_invoice()
                # Validate Invoice and Paid
                if expense.state == 'done':
                    invoice = self._auto_validate_invoice(expense)
                    if invoice and invoice.state == 'open':
                        self._auto_validate_payment(invoice)
                self._cr.commit()
            except Exception:
                _logger.exception("Failed Action for %s" % (expense.number,))
                self._cr.rollback()

    @api.model
    def _auto_validate_invoice(self, expense):
        invoices = self.env['account.invoice'].\
            search([('expense_id', '=', expense.id)])
        if not invoices:
            return False
        invoice = invoices[0]
        invoice.write({'supplier_invoice_number': 'X',
                       'payment_type': 'cheque'})
        if invoice.state == 'draft':
            invoice.signal_workflow('invoice_open')
        return invoice

    @api.model
    def _auto_validate_payment(self, invoice):
        # Create Payment and Validate It!
        account = self.env['account.account'].search(
            [('type', '=', 'payable'),
             ('currency_id', '=', False)],
            limit=1)[0]
        voucher = self.env['account.voucher'].create({
            'date': fields.Date.context_today(self),
            'amount': invoice.amount_total,
            'account_id': account.id,
            'partner_id': invoice.partner_id.id,
            'type': 'payment',
            'date_value': fields.Date.context_today(self),
        })
        val = voucher.\
            with_context({
                'filter_by_invoice_ids': [invoice.id]}).\
            onchange_partner_id(
                voucher.partner_id.id,
                voucher.journal_id.id,
                voucher.amount,
                voucher.currency_id.id,
                voucher.type,
                voucher.date
            )
        voucher_lines = [(0, 0, line) for
                         line in val['value']['line_dr_ids']]
        voucher.write({'line_dr_ids': voucher_lines})
        if not voucher.writeoff_amount:
            voucher.signal_workflow('proforma_voucher')
