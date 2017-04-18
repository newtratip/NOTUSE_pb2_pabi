# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.tools import float_round as round
from openerp.exceptions import ValidationError, Warning as UserError


class BudgetFundExpenseGroup(models.Model):
    _name = "budget.fund.expense.group"
    _description = "Expense Group"

    name = fields.Char(
        string='Name',
        copy=False,
    )


class BudgetFundRule(models.Model):
    _name = "budget.fund.rule"
    _description = "Rule for Budget's Fund vs Project"

    name = fields.Char(
        string='Number',
        index=True,
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    template = fields.Boolean(
        string='Template',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    template_id = fields.Many2one(
        'budget.fund.rule',
        string='Template',
        domain="[('template', '=', True), ('fund_id', '=', fund_id)]",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    fund_id = fields.Many2one(
        'res.fund',
        string='Fund',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    fund_rule_line_ids = fields.One2many(
        'budget.fund.rule.line',
        'fund_rule_id',
        string='Spending Rules',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Spending rule for activity groups",
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirmed', 'Confirmed'),
         ('cancel', 'Cancelled'),
         ],
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
    )

    @api.multi
    @api.constrains('project_id', 'template')
    def _check_project_template(self):
        for rec in self:
            if rec.template and rec.project_id:
                raise ValidationError(
                    _('This is a tempalte rule, no project allowed!'))
            if not rec.template and not rec.project_id:
                raise ValidationError(
                    _('This is a project rule, template must not checked!'))

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    @api.one
    @api.constrains('name', 'template', 'fund_id', 'project_id')
    def _check_unique(self):
        if self.template:
            if len(self.search([('template', '=', True),
                                ('name', '=', self.name),
                                ('fund_id', '=', self.fund_id.id)])) > 1:
                raise UserError(_('Duplicated Template Name'))
        else:
            if len(self.search([('template', '=', False),
                                ('project_id', '=', self.project_id.id),
                                ('fund_id', '=', self.fund_id.id)])) > 1:
                raise UserError(_('Duplicated Fund Rule'))

    @api.one
    @api.constrains('fund_rule_line_ids',
                    'fund_rule_line_ids.account_ids')
    def _check_fund_rule_line_ids(self):
        account_ids = []
        for line in self.fund_rule_line_ids:
            if len(set(line.account_ids._ids).
                   intersection(account_ids)) > 0:
                raise UserError(_('Duplicated GL Account'))
            else:
                account_ids += line.account_ids._ids

    @api.onchange('fund_id')
    def _onchange_fund_id(self):
        self.template_id = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        self.fund_rule_line_ids = []
        Line = self.env['budget.fund.rule.line']
        for line in self.template_id.fund_rule_line_ids:
            new_line = Line.new()
            new_line.expense_group_id = line.expense_group_id
            new_line.account_ids = line.account_ids
            new_line.max_spending_percent = line.max_spending_percent
            self.fund_rule_line_ids += new_line

    @api.model
    def create(self, vals):
        if not vals.get('template', False):
            vals['name'] = \
                self.env['ir.sequence'].get('budget.fund.rule') or '/'
        return super(BudgetFundRule, self).create(vals)

    @api.model
    def _get_matched_fund_rule(self, project_fund_vals):
        rules = []
        for val in project_fund_vals:
            project_id, fund_id = val[0], val[1]
            # Find matching rule for this Project + Funding
            rule = self.env['budget.fund.rule'].\
                search([('project_id', '=', project_id),
                        ('fund_id', '=', fund_id),
                        ('template', '=', False),
                        ('state', 'in', ['draft', 'confirmed'])
                        ])
            if len(rule) == 1:
                rules.append(rule)
            elif len(rule) > 1:
                project = self.env['res.project'].browse(project_id)
                fund = self.env['res.fund'].browse(fund_id)
                raise ValidationError(
                    _('More than 1 rule is found for project %s / fund %s!') %
                    (project.code, fund.name))
        return rules

    @api.model
    def document_check_fund_spending(self, doc_lines, amount_field):
        res = {'budget_ok': True,
               'message': False}
        Budget = self.env['account.budget']
        if not doc_lines:
            return res
        # Project / Fund unique (to find matched fund rules
        project_fund_vals = Budget._get_doc_field_combination(doc_lines,
                                                              ['project_id',
                                                               'fund_id'])
        # Find all matching rules for this transaction
        rules = self._get_matched_fund_rule(project_fund_vals)
        # Check against each rule
        for rule in rules:
            project = rule.project_id
            fund = rule.fund_id
            # 1) If rule is defined for a Project/Fund, Activity must be valid
            rule_activity_ids = []
            for rule_line in rule.fund_rule_line_ids:
                rule_activity_ids += [x.id for x in rule_line.activity_ids]
            xlines = filter(lambda l:
                            l['project_id'] == project.id and
                            l['fund_id'] == fund,
                            doc_lines)
            activity_ids = [x.activity.id for x in xlines]
            # Only activity in doc_lines that match rule is allowed
            if not (set(activity_ids) < set(rule_activity_ids)):
                res['budget_ok'] = False
                res['message'] = _('Selected Activity is '
                                   'not usable for Fund %s') % \
                    (rule.fund_id.name,)
                return res
            # 2) Check each rule line
            for rule_line in rule.fund_rule_line_ids:
                activity_ids = rule_line.activity_ids._ids
                xlines = filter(lambda l:
                                l['project_id'] == project.id and
                                l['fund_id'] == fund.id and
                                l['activity_id'] in activity_ids,
                                doc_lines)
                amount = sum(map(lambda l: l[amount_field], xlines))
                if amount <= 0.00:
                    continue
                res = self.check_fund_activity_spending(rule_line.id,
                                                        amount)
                if not res['budget_ok']:
                    return res
        return res

    @api.model
    def check_fund_activity_spending(self, fund_rule_line_id, amount):
        res = {'budget_ok': True,
               'message': False}
        rule_line = self.env['budget.fund.rule.line'].browse(fund_rule_line_id)
        if rule_line.fund_rule_id.state in ('draft'):
            res['budget_ok'] = False
            res['message'] = _('Rules of Fund %s / Project %s '
                               'has been set, but still in draft state!') % \
                (rule_line.fund_rule_id.fund_id.name,
                 rule_line.fund_rule_id.project_id.code)
            return res
        max_percent = rule_line.max_spending_percent
        expense_group = rule_line.expense_group_id
        if not rule_line.amount or rule_line.amount <= 0:
            res['budget_ok'] = False
            res['message'] = _('No amount has been allocated for '
                               'Expense Group %s!') % (expense_group.name,)
            return res
        future_amount = rule_line.amount_consumed + amount
        spending_percent = 100.0 * future_amount / rule_line.amount
        if spending_percent > max_percent:
            res['budget_ok'] = False
            res['message'] = _('Amount exceeded maximum spending '
                               'for Expense Group %s!\n'
                               '(%s%% vs %s%%)') % \
                (expense_group.name,
                 round(spending_percent, 2),
                 round(max_percent, 2))
            return res
        return res


class BudgetFundRuleLine(models.Model):
    _name = "budget.fund.rule.line"
    _description = "Spending Rule specific for Activity Groups"

    fund_rule_id = fields.Many2one(
        'budget.fund.rule',
        string='Funding Rule',
        index=True,
        ondelete='cascade',
    )
    expense_group_id = fields.Many2one(
        'budget.fund.expense.group',
        string='Expense Group',
        required=True,
        ondelete='restrict',
    )
    project_id = fields.Many2one(
        'res.project',
        related='fund_rule_id.project_id',
        string='Project',
    )
    fund_id = fields.Many2one(
        'res.fund',
        related='fund_rule_id.fund_id',
        string='Fund',
    )
    account_ids = fields.Many2many(
        'account.account',
        'fund_rule_line_account_rel',
        'fund_rule_line_id', 'account_id',
        string='GL Account',
        domain=[('type', '!=', 'view')],
        required=True,
    )
    activity_ids = fields.Many2many(
        'account.activity',
        'fund_rule_line_activity_rel',
        'fund_rule_line_id', 'activity_id',
        string='Activities',
        compute='_compute_activity_ids',
        store=True,
        readonly=True,
    )
    amount = fields.Float(
        string='Funded Amount',
        default=0,
    )
    amount_consumed = fields.Float(
        string='Consumed Amount',
        compute='_compute_amount_consumed',
    )
    max_spending_percent = fields.Integer(
        string='Max Spending (%)',
        default=100.0,
        required=True,
    )

    @api.multi
    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if not rec.fund_rule_id.template and not rec.amount:
                raise ValidationError(_('Funded Amount must not be zero!'))

    @api.multi
    @api.depends()
    def _compute_amount_consumed(self):
        for rec in self:
            if not rec.activity_ids or not rec.project_id or not rec.fund_id:
                rec.amount_consumed = 0.0
                continue
            self._cr.execute("""
                select sum(case when budget_method = 'expense'
                            then amount else -amount end) as expense
                from budget_consume_report
                where project_id = %s
                    and fund_id = %s
                    and activity_id in %s
            """, (rec.project_id.id,
                  rec.fund_id.id,
                  rec.activity_ids._ids,))
            cr_res = self._cr.fetchone()
            rec.amount_consumed = cr_res[0]
        return

    @api.multi
    @api.depends('account_ids')
    def _compute_activity_ids(self):
        Activity = self.env['account.activity']
        for rec in self:
            rec.activity_ids = Activity.search(
                [('account_id', 'in', rec.account_ids.ids)])
        return
