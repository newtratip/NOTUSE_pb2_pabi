# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError

DUE_TYPES = [('1', 'Due in 10 days'),
             ('2', 'Due in 5 days'),
             ('3', 'Due now'),
             ]
DUE_TYPE_DAYS = {'3': 10, '2': 5, '1': 0}


class PABIAdvanceDunningLetter(models.Model):
    _name = 'pabi.advance.dunning.letter'

    name = fields.Char(
        string='Number',
        index=True,
        copy=False,
        readonly=True,
    )
    date_print = fields.Date(
        string='Print Date',
        default=lambda self: fields.Date.context_today(self),
        readonly=True,
    )
    print_pdf = fields.Boolean(
        string='Print as PDF',
        default=True,
    )
    send_email = fields.Boolean(
        string='Send Email',
        default=True,
    )
    dunning_list = fields.One2many(
        'pabi.advance.dunning.letter.line',
        'dunning_id',
        string='Dunning List',
    )
    dunning_list_1 = fields.One2many(
        'pabi.advance.dunning.letter.line',
        'dunning_id',
        string='On due date',
        domain=[('due_type', '=', '1')]
    )
    dunning_list_2 = fields.One2many(
        'pabi.advance.dunning.letter.line',
        'dunning_id',
        string='5 days to due date',
        domain=[('due_type', '=', '2')]
    )
    dunning_list_3 = fields.One2many(
        'pabi.advance.dunning.letter.line',
        'dunning_id',
        string='10 days to due date',
        domain=[('due_type', '=', '3')]
    )
    # Temporary Fields todo remove
    group_email = fields.Char(
        string="Group Email",
        default="acf-adv@nstda.or.th",
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('done', 'Done'),
         ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
    )
    # For search
    expense_id = fields.Many2one(
        'hr.expense.expense',
        string='Expense',
        related='dunning_list.expense_id',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='dunning_list.employee_id',
    )

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('advance.dunning') or '/'
        return super(PABIAdvanceDunningLetter, self).create(vals)

    @api.model
    def _search_domain(self, due_type, date_due):
        search_domain = [('is_employee_advance', '=', True),
                         ('state', '=', 'paid'),
                         ('amount_to_clearing', '>', 0.0),
                         ('date_due', '<=', date_due), ]
        if due_type == '1':  # 10 days
            search_domain += [('date_dunning_1', '=', False),
                              ('date_dunning_2', '=', False),
                              ('date_dunning_3', '=', False)]
        if due_type == '2':  # 5 days
            search_domain += [('date_dunning_2', '=', False),
                              ('date_dunning_3', '=', False)]
        if due_type == '3':  # Now
            search_domain += [('date_dunning_3', '=', False)]
        return search_domain

    @api.model
    def _prepare_line(self, expense, due_type):
        line = {'expense_id': expense.id,
                'due_type': due_type,
                }
        # TODO: assign email based on command lines
        if due_type == '1':  # Due Now
            line.update({'to_employee_ids': [],
                        'cc_employee_ids': [expense.employee_id.id], })
        if due_type == '2':
            line.update({'to_employee_ids': [],
                        'cc_employee_ids': [expense.employee_id.id], })
        if due_type == '3':
            line.update({'to_employee_ids': [expense.employee_id.id],
                        'cc_employee_ids': [], })
        return line

    @api.model
    def default_get(self, field_list):
        res = super(PABIAdvanceDunningLetter, self).default_get(field_list)
        Expense = self.env['hr.expense.expense']
        today = datetime.strptime(
            fields.Date.context_today(self), '%Y-%m-%d').date()
        expense_ids = []
        for due_type in ('3', '2', '1'):  # 3 types of notice,
            res['dunning_list_' + due_type] = []
            date_due = today + relativedelta(days=DUE_TYPE_DAYS[due_type])
            expenses = Expense.search(self._search_domain(due_type, date_due))
            for expense in expenses:
                if expense.id in expense_ids:  # Send only 1 letter.
                    continue
                line = self._prepare_line(expense, due_type)
                res['dunning_list_' + due_type].append(line)
                expense_ids.append(expense.id)
        return res

    @api.multi
    def run_report(self):
        self.ensure_one()
        if not self.send_email and not self.print_pdf:
            return {}

        line_ids = [x.id for x in self.dunning_list]
        if not line_ids:
            raise UserError(_('No dunning letter to print/email!'))

        # Update date for each advance
        list_1 = self.dunning_list.filtered(lambda l: l.due_type == '1')
        list_2 = self.dunning_list.filtered(lambda l: l.due_type == '2')
        list_3 = self.dunning_list.filtered(lambda l: l.due_type == '3')
        today = fields.Date.context_today(self)
        list_1.mapped('expense_id').write({'date_dunning_1': today})
        list_2.mapped('expense_id').write({'date_dunning_2': today})
        list_3.mapped('expense_id').write({'date_dunning_3': today})

        # Email
        # Send dunning letter by email to each of selected employees
        if self.send_email:
            self._send_dunning_letter_by_mail()
        self.write({'state': 'done',
                    'send_email': False,
                    })

        # Print PDF
        if not self.print_pdf:
            return {}
        data = {'parameters': {}}
        report_name = 'advance_dunning_letter'
        data['parameters']['ids'] = line_ids
        data['parameters']['date_print'] = fields.Date.context_today(self)
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res

    @api.model
    def _send_dunning_letter_by_mail(self):
        if not self.dunning_list:
            return True

        templates = {
            '1': 'pabi_advance_dunning_letter.email_template_edi_10_due_days',
            '2': 'pabi_advance_dunning_letter.email_template_edi_5_due_days',
            '3': 'pabi_advance_dunning_letter.email_template_edi_0_due_days',
        }

        DUE_DAYS = {'1': 10, '2': 5, '3': 0}

        if not self.group_email:
            raise UserError(
                _('Please enter valid email address for group email!'))

        for line in self.dunning_list:
            template_name = templates[line.due_type]
            template = False
            try:
                template = self.env.ref(template_name)
            except:
                pass

            if not self.group_email:
                raise UserError(
                    _('Please enter valid email address for group email!'))

            if template:
                ctx = self.env.context.copy()
                ctx.update({
                    'due_days': DUE_DAYS[line.due_type],
                    'date_print': fields.Date.context_today(self),
                    'email_attachment': True,
                    'ids': [line.id]
                })
                if line.expense_id:
                    to_email = False
                    cc_email = self.group_email
                    for to_line in line.to_employee_ids:
                        if to_line.work_email:
                            if not to_email:
                                to_email = to_line.work_email
                            else:
                                to_email = to_email + ',' + to_line.work_email

                    for cc_line in line.cc_employee_ids:
                        if cc_line.work_email:
                            cc_email = cc_email + ',' + cc_line.work_email
                    template.email_to = to_email
                    template.email_cc = cc_email
                    template.with_context(ctx).send_mail(line.expense_id.id)
        return True


class PABIAdvanceDunningLetterLine(models.Model):
    _name = 'pabi.advance.dunning.letter.line'

    dunning_id = fields.Many2one(
        'pabi.advance.dunning.letter',
        string='Dunning',
        readonly=True,
        index=True,
        ondelete='cascade',
    )
    due_type = fields.Selection(
        DUE_TYPES,
        string='Due type',
        required=True,
    )
    expense_id = fields.Many2one(
        'hr.expense.expense',
        string='Employee Advance',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        related='expense_id.employee_id',
        string='Employee',
        readonly=True,
    )
    date_due = fields.Date(
        string='Date Due',
        related='expense_id.date_due',
        readonly=True,
    )
    amount_to_clearing = fields.Float(
        string='Amount Remaining',
        related='expense_id.amount_to_clearing',
        readonly=True,
    )
    description = fields.Char(
        string='Description',
        related='expense_id.name',
        readonly=True,
    )
    send_email = fields.Boolean(
        related='dunning_id.send_email',
        string='Send Email',
    )
    to_employee_ids = fields.Many2many(
        'hr.employee',
        'to_employee_dunning_rel',
        'employee_id',
        'line_id',
        string="TO",
    )
    cc_employee_ids = fields.Many2many(
        'hr.employee',
        'cc_employee_dunning_rel',
        'employee_id',
        'line_id',
        string="CC",
    )
    date_dunning_1 = fields.Date(
        string='Notice 1',
        related='expense_id.date_dunning_1',
        readonly=True,
    )
    date_dunning_2 = fields.Date(
        string='Notice 2',
        related='expense_id.date_dunning_2',
        readonly=True,
    )
    date_dunning_3 = fields.Date(
        string='Notice 3',
        related='expense_id.date_dunning_3',
        readonly=True,
    )
