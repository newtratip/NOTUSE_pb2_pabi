# -*- coding: utf-8 -*-

from openerp import models, fields, api, _


class HRExpense(models.Model):
    _inherit = 'hr.expense.expense'
    _order = "id"

    # editable only on draft state
    employee_id = fields.Many2one(
        readonly=True, states={'draft': [('readonly', False)]},
    )
    name = fields.Char(
        readonly=True, states={'draft': [('readonly', False)]},
    )
    currency_id = fields.Many2one(
        readonly=True, states={'draft': [('readonly', False)]},
    )
    operating_unit_id = fields.Many2one(
        readonly=True, states={'draft': [('readonly', False)]},
    )
    # --
    approver_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    apweb_ref_url = fields.Char(
        string='PABI Web Ref.',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    date = fields.Date(
        string='Approved Date',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    user_valid = fields.Many2one(
        string='Accepted By',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    date_back = fields.Date(
        string='Back from seminar',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    date_due = fields.Date(
        string='Due Date',
        related='advance_due_history_ids.date_due',
        store=True,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    receive_method = fields.Selection(
        [('salary_bank', 'Salary Bank Account'),
         ('other_bank', 'Other Banks')],
        string='Receive Method',
        default='salary_bank',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    employee_bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    supplier_text = fields.Char(
        string='Supplier Name',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('cancelled', 'Rejected'),
         ('confirm', 'Wait for Accept'),
         ('accepted', 'Accepted'),
         ('done', 'Waiting Payment'),
         ('invoice_except', 'Invoice Exception'),
         ('paid', 'Paid'),
         ]
    )
    advance_type = fields.Selection(
        [('buy_product', 'Buy Product/Material'),
         ('attend_seminar', 'Attend Seminar'),
         ],
        readonly=True, states={'draft': [('readonly', False)]},
    )
    advance_due_history_ids = fields.One2many(
        'hr.expense.advance.due.history',
        'expense_id',
        string='Due History',
        readonly=True,
    )
    attendee_employee_ids = fields.One2many(
        'hr.expense.attendee.employee',
        'expense_id',
        string='Attendee / Employee',
        copy=True,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    attendee_external_ids = fields.One2many(
        'hr.expense.attendee.external',
        'expense_id',
        string='Attendee / External',
        copy=True,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        compute='_compute_project_section',
        store=True,
        readonly=True,
        help="Show project, only if all lines use the same project",
    )
    employee_section_id = fields.Many2one( # Section of Employee, for Security
        'res.section',
        string='Section',
        related='employee_id.section_id',
        store=True,
        readonly=True,
        help="Employee Section to be used for security purposes."
        "User in group Expense Officer (restrict) will see only his sections",
    )
    section_id = fields.Many2one( # Selected Sectoin
        'res.section',
        string='Section',
        compute='_compute_project_section',
        store=True,
        help="Show section, only if all lines use the same section",
        readonly=True,
    )
    project_code = fields.Char(
        string='Project',
        related='project_id.code',
        store=True,
        readonly=True,
    )
    section_code = fields.Char(
        string='Section',
        related='section_id.code',
        store=True,
        readonly=True,
    )
    reason_bypass_procure = fields.Char(
        string='Reason purchase bypass procurement',
        readonly=True,
    )
    remark = fields.Text(
        string='Note for Advance',
    )
    activity_group_ids = fields.Many2many(
        'account.activity.group',
        string="Activity Groups",
        compute='_compute_activity_groups',
        store=True,
    )

    @api.multi
    @api.constrains('line_ids')
    def _check_line_ids(self):
        chart_fields = {
            'project_id': 
            self.advance_expense_id.line_ids.mapped('project_id')._ids,
            'section_id': 
            self.advance_expense_id.line_ids.mapped('section_id')._ids,
            'invest_asset_id': 
            self.advance_expense_id.line_ids.mapped('invest_asset_id')._ids,
            'invest_construction_phase_id': 
            self.advance_expense_id.line_ids.mapped(
                'invest_construction_phase_id')._ids,
        }
        msg = _("You are selecting dimension which "
                "has not been used in Advance %s." 
                % self.advance_expense_id.name_get()[0][1])

        for line in self.line_ids:
            for field in chart_fields:
                if line[field]:
                    if line[field].id not in chart_fields[field]:
                        raise Warning(msg)

    @api.multi
    @api.depends(
        'line_ids',
        'line_ids.activity_group_id')
    def _compute_activity_groups(self):
        for expense in self:
            if expense.line_ids:
                expense_ids = []
                for line in expense.line_ids:
                    if line.activity_group_id:
                        expense_ids.append(line.activity_group_id.id)
                expense.activity_group_ids = expense_ids

    @api.multi
    @api.depends('line_ids', 'line_ids.project_id', 'line_ids.section_id')
    def _compute_project_section(self):
        for rec in self:
            projects = rec.line_ids.\
                filtered(lambda x: x.project_id).mapped('project_id')
            sections = rec.line_ids.\
                filtered(lambda x: x.section_id).mapped('section_id')
            rec.project_id = len(projects) == 1 and projects[0] or False
            rec.section_id = len(sections) == 1 and sections[0] or False

    @api.model
    def _prepare_inv_header(self, partner_id, expense):
        res = super(HRExpense, self)._prepare_inv_header(partner_id,
                                                         expense)
        if self._context.get('amount_expense_request', False):
            res.update({'amount_expense_request':
                        self._context.get('amount_expense_request')})
        else:
            res.update({'amount_expense_request':
                        expense.amount})
        return res

    @api.multi
    def action_invoice_except(self):
        for expense in self:
            expense.write({'state': 'invoice_except'})
        return True

    @api.multi
    def action_ignore_exception(self):
        for expense in self:
            set_paid = True
            for invoice in expense.invoice_ids:
                if invoice.state not in ('paid', 'cancel'):
                    set_paid = False
            if set_paid:
                expense.signal_workflow('except_to_paid')
        return True

    @api.multi
    def action_recreate_invoice(self):
        for expense in self:
            for invoice in expense.invoice_ids:
                if invoice.state == 'cancel' and not invoice.invoice_ref_id:
                    root_invoice = invoice
                    while root_invoice.invoice_ref_id:
                        root_invoice = root_invoice.invoice_ref_id

                    new_invoice_val = root_invoice.copy_data()[0]
                    new_invoice_val.update({
                        'amount_expense_request':
                            root_invoice.amount_expense_request,
                        'expense_id': root_invoice.expense_id.id,
                        'invoice_ref_id': invoice.id,
                    })
                    new_invoice = self.env['account.invoice'].\
                        create(new_invoice_val)
                    expense.invoice_id = new_invoice
            expense.signal_workflow('except_to_done')
        return True


class HRExpenseAdvanceDueHistory(models.Model):
    _name = 'hr.expense.advance.due.history'
    _order = 'write_date desc'

    expense_id = fields.Many2one(
        'hr.expense.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    date_due = fields.Date(
        string='New Due Date',
        readonly=True,
    )
    write_uid = fields.Many2one(
        'res.users',
        string='Updated By',
        readonly=True,
    )
    write_date = fields.Datetime(
        string='Updated Date',
        readonly=True,
    )


class HRExpenseAttendeeEmployee(models.Model):
    _name = 'hr.expense.attendee.employee'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    expense_id = fields.Many2one(
        'hr.expense.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )
    position_id = fields.Many2one(
        'hr.position',
        related='employee_id.position_id',
        string='Position',
        store=True,
    )
    section_id = fields.Many2one(
        'res.section',
        related='employee_id.section_id',
        string='Section',
        store=True,
    )


class HRExpenseAttendeeExternal(models.Model):
    _name = 'hr.expense.attendee.external'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    expense_id = fields.Many2one(
        'hr.expense.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    attendee_name = fields.Char(
        string='Attendee Name',
    )
    position = fields.Char(
        string='Position',
    )
    organization = fields.Char(
        string='Organization',
    )


class HRExpenseClearing(models.Model):
    _inherit = 'hr.expense.clearing'

    validate_user_id = fields.Many2one(
        'res.users',
        string='Validated by',
        # related='invoice_id.validate_user_id',
    )


class HRExpenseRule(models.Model):
    _name = "hr.expense.rule"

    activity_id = fields.Many2one(
        'account.activity',
        string='Activity',
        required=True,
    )
    position = fields.Char(
        string='Position',
    )
    condition_1 = fields.Char(
        string='Condition 1',
    )
    condition_2 = fields.Char(
        string='Condition 2',
    )
    uom = fields.Char(
        string='UoM',
    )
    amount = fields.Float(
        string='Amount',
        default=0.0,
        required=True,
    )
    _sql_constraints = [
        ('rule_unique',
         'unique(activity_id, position, condition_1, condition_2, uom)',
         'Expense Regulation must be unique!'),
    ]
