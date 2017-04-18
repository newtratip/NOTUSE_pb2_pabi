# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, api, fields, _
from openerp.exceptions import Warning as UserError
from openerp.addons.pabi_base.models.res_investment_structure \
    import CONSTRUCTION_PHASE


class ResInvestConstruction(models.Model):
    _inherit = 'res.invest.construction'

    code = fields.Char(
        readonly=True,
        default='/',
        copy=False,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submit', 'Submitted'),
         ('approve', 'Approved'),
         ('reject', 'Rejected'),
         ('delete', 'Deleted'),
         ('cancel', 'Cancelled'),
         ('close', 'Closed'),
         ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        default='draft',
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_end = fields.Date(
        string='End Date',
        required=False,
    )
    pm_employee_id = fields.Many2one(
        'hr.employee',
        string='Project Manager',
        required=True,
    )
    section_id = fields.Many2one(
        'res.section',
        string='Project Manager Section',
        required=True,
    )
    org_id = fields.Many2one(
        'res.org',
        string='Project Manager Org',
        related='section_id.org_id',
        store=True,
        readonly=True,
    )
    mission_id = fields.Many2one(
        'res.mission',
        string='Core Mission',
        required=True,
    )
    amount_budget_plan = fields.Float(
        string='Planned Budget',
        compute='_compute_amount_budget_plan',
    )
    amount_budget_approve = fields.Float(
        string='Approved Budget',
        default=0.0,
    )
    month_duration = fields.Integer(
        string='Duration (months)',
    )
    operation_area = fields.Char(
        string='Operation Area',
    )
    date_expansion = fields.Date(
        string='Expansion Date',
    )
    approval_info = fields.Text(
        string='Approval info',
    )
    project_readiness = fields.Text(
        string='Project Readiness',
    )
    reason = fields.Text(
        string='Reason',
    )
    expected_result = fields.Text(
        string='Expected Result',
    )
    budget_plan_ids = fields.One2many(
        'res.invest.construction.budget.plan',
        'invest_construction_id',
        string='Budget Planning',
    )
    _sql_constraints = [
        ('number_uniq', 'unique(code)',
         'Constuction Project Code must be unique!'),
    ]

    @api.multi
    @api.depends('budget_plan_ids.amount_plan')
    def _compute_amount_budget_plan(self):
        for rec in self:
            rec.amount_budget_plan = \
                sum([x.amount_plan for x in rec.budget_plan_ids])

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].\
                next_by_code('invest.construction')
        return super(ResInvestConstruction, self).create(vals)

    @api.onchange('pm_employee_id')
    def _onchange_user_id(self):
        employee = self.pm_employee_id
        self.section_id = employee.section_id

    @api.onchange('month_duration', 'date_start')
    def _onchange_date(self):
        date_start = datetime.strptime(self.date_start, '%Y-%m-%d').date()
        date_end = date_start + relativedelta(months=self.month_duration)
        self.date_end = date_end.strftime('%Y-%m-%d')
        self._prepare_budget_plan_line(self.date_start, self.date_end)

    @api.model
    def _prepare_budget_plan_line(self, date_start, date_end):
        self.budget_plan_ids = False
        Fiscal = self.env['account.fiscalyear']
        Plan = self.env['res.invest.construction.budget.plan']
        if date_start and date_end:
            fiscal_start_id = Fiscal.find(date_start)
            fiscal_end_id = Fiscal.find(date_end)
            fiscal_start = Fiscal.browse(fiscal_start_id)
            fiscal_end = Fiscal.browse(fiscal_end_id)
            fiscal_year = int(fiscal_start.name)
            while fiscal_year <= int(fiscal_end.name):
                fiscal = Fiscal.search([('name', '=', str(fiscal_year))])
                if fiscal:
                    plan = Plan.new()
                    plan.fiscalyear_id = fiscal
                    plan.amount_plan = 0.0
                    self.budget_plan_ids += plan
                fiscal_year += 1
        return True

    @api.multi
    def action_create_phase(self):
        for rec in self:
            if rec.phase_ids:
                continue
            phases = []
            i = 1
            for phase in sorted(CONSTRUCTION_PHASE.items()):
                phases.append((0, 0, {'sequence': i, 'phase': phase[0]}))
                i += 1
            rec.write({'phase_ids': phases})

    # Statuses
    @api.multi
    def action_submit(self):
        self.write({'state': 'submit'})

    @api.multi
    def action_approve(self):
        self.write({'state': 'approve'})

    @api.multi
    def action_reject(self):
        self.write({'state': 'reject'})

    @api.multi
    def action_delete(self):
        self.write({'state': 'delete'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_close(self):
        self.write({'state': 'close'})

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})


class RestInvestConstructionPhase(models.Model):
    _inherit = 'res.invest.construction.phase'

    active = fields.Boolean(
        string='Active',
        compute='_compute_active',
        store=True,
        help="Phase is activated only when approved",
    )
    code = fields.Char(
        readonly=True,
        default='/',
        copy=False,
    )
    org_id = fields.Many2one(
        'res.org',
        string='Org',
        related='invest_construction_id.org_id',
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submit', 'Submitted'),
         ('approve', 'Approved'),
         ('reject', 'Rejected'),
         ('delete', 'Deleted'),
         ('cancel', 'Cancelled'),
         ('close', 'Closed'),
         ],
        string='Status',
        readonly=True,
        required=True,
        copy=False,
        default='draft',
    )
    amount_phase_approve = fields.Float(
        string='Approved Budget (Phase)',
        default=0.0,
    )
    amount_phase_plan = fields.Float(
        string='Planned Budget (Phase)',
        compute='_compute_amount_phase_plan',
    )
    amount_phase_diff = fields.Float(
        string='Unplanned Budget (Phase)',
        compute='_compute_amount_phase_plan',
    )
    month_duration = fields.Integer(
        string='Duration (months)',
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_end = fields.Date(
        string='End Date',
        required=False,
    )
    date_expansion = fields.Date(
        string='Date Expansion',
    )
    contract_day_duration = fields.Integer(
        string='Contract Duration (days)',
    )
    contract_date_start = fields.Date(
        string='Contract Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    contract_date_end = fields.Date(
        string='Contract End Date',
        required=False,
    )
    contract_number = fields.Char(
        string='Contract Number',
    )
    phase_plan_ids = fields.One2many(
        'res.invest.construction.phase.plan',
        'invest_construction_phase_id',
        string='Budget Planning (Phase)',
    )
    fiscalyear_ids = fields.Many2many(
        'account.fiscalyear',
        'invest_construction_fiscalyear_rel',
        'invest_construction_id', 'fiscalyear_id',
        string='Related Fiscal Years',
        compute='_compute_fiscalyear_ids',
        store=True,
        help="All related fiscal years for this phases"
    )
    to_sync = fields.Boolean(
        string='To Sync',
        compute='_compute_to_sync',
        store=True,
        help="Some changes left to be synced"
    )
    sync_ids = fields.One2many(
        'res.invest.construction.phase.sync',
        'phase_id',
        string='Sync History',
        copy=False,
    )
    _sql_constraints = [
        ('number_uniq', 'unique(code)',
         'Constuction Phase Code must be unique!'),
    ]

    @api.model
    def _get_changed_plan_fiscalyear(self, vals):
        # For changes, find the related fiscalyear_ids and update the sync
        PhasePlan = self.env['res.invest.construction.phase.plan']
        # Update (1)
        changed_plans = filter(lambda x: x[0] == 1,
                               vals.get('phase_plan_ids'))
        plan_ids = map(lambda x: x[1], changed_plans)
        plans = PhasePlan.browse(plan_ids)
        year_ids = [x.fiscalyear_id.id for x in plans]
        # Create (0)
        changed_plans = filter(lambda x: x[0] == 0 and x[1] is False,
                               vals.get('phase_plan_ids'))
        year_ids += map(lambda x: x[2].get('fiscalyear_id'), changed_plans)
        return year_ids

    @api.multi
    def write(self, vals):
        if vals.get('phase_plan_ids', False):
            year_ids = self._get_changed_plan_fiscalyear(vals)
            for phase in self:
                phase.sync_ids.filtered(lambda l: l.fiscalyear_id.id
                                        in year_ids).write({'synced': False})
        return super(RestInvestConstructionPhase, self).write(vals)

    @api.multi
    @api.depends('state')
    def _compute_active(self):
        for rec in self:
            rec.active = rec.state == 'approve'

    @api.multi
    @api.depends('phase_plan_ids.amount_plan')
    def _compute_amount_phase_plan(self):
        for rec in self:
            rec.amount_phase_plan = \
                sum([x.amount_plan for x in rec.phase_plan_ids])
            rec.amount_phase_diff = \
                rec.amount_phase_approve - rec.amount_phase_plan

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            prefix = 'N/A-'
            if vals.get('invest_construction_id', False):
                project = self.env['res.invest.construction'].\
                    browse(vals.get('invest_construction_id'))
                prefix = str(project.code) + '-'
            vals['code'] = prefix + '{:02d}'.format(vals.get('sequence', 0))
        return super(RestInvestConstructionPhase, self).create(vals)

    @api.onchange('month_duration', 'date_start')
    def _onchange_date(self):
        date_start = datetime.strptime(self.date_start, '%Y-%m-%d').date()
        date_end = date_start + relativedelta(months=self.month_duration)
        self.date_end = date_end.strftime('%Y-%m-%d')
        self._prepare_phase_plan_line(self.date_start, self.date_end)

    @api.model
    def _prepare_phase_plan_line(self, date_start, date_end):
        self.phase_plan_ids = False
        Period = self.env['account.period']
        Plan = self.env['res.invest.construction.phase.plan']
        date = date_start
        if date and date_end:
            while date <= date_end:
                period = Period.find(date)
                plan = Plan.new()
                plan.calendar_period_id = period.id
                plan.amount_plan = 0.0
                self.phase_plan_ids += plan
                next_period = Period.next(period, 1)
                date = next_period.date_start
                if not next_period:
                    raise UserError(
                        _('No period configured for the target end date'))
        return True

    @api.multi
    @api.depends('phase_plan_ids.fiscalyear_id')
    def _compute_fiscalyear_ids(self):
        for phase in self:
            fiscalyear_ids = [x.fiscalyear_id.id
                              for x in phase.phase_plan_ids]
            phase.fiscalyear_ids = list(set(fiscalyear_ids))

    @api.multi
    @api.depends('sync_ids.synced')
    def _compute_to_sync(self):
        for phase in self:
            fiscalyear_ids = [x.fiscalyear_id.id
                              for x in phase.phase_plan_ids]
            phase.fiscalyear_ids = list(set(fiscalyear_ids))
            to_syncs = phase.sync_ids.filtered(lambda l: l.synced is False)
            phase.to_sync = len(to_syncs) > 0 and True or False

    @api.model
    def _prepare_mo_dict(self, fiscalyear):
        month = int(fiscalyear.date_start[5:7])
        mo_dict = {}
        for i in range(12):
            mo_dict.update({month: 'm' + str(i + 1)})
            month += 1
            if month > 12:
                month = 1
        vals = dict([(v, False) for v in mo_dict.values()])
        return (mo_dict, vals)

    @api.multi
    def sync_phase_to_budget_line(self, fiscalyear_ids=False):
        """
        fiscalyear_ids specify which year to sync, otherwise, all sync.
        only sync if synced=False
        """
        for phase in self:
            print fiscalyear_ids
            print phase.sync_ids
            # Find phase with vaild sync history (has been pulled before)
            phase_syncs = not fiscalyear_ids and phase.sync_ids or \
                phase.sync_ids.filtered(lambda l: l.fiscalyear_id.id
                                        in fiscalyear_ids)
            print phase_syncs
            if not phase_syncs:
                continue
            for sync in phase_syncs:
                print sync
                # No valid budate line reference, or already synced, ignore it
                # (need to pull from budget control first)
                if not sync.sync_budget_line_id or sync.synced:
                    continue
                # Prepare update dict
                fiscalyear = sync.fiscalyear_id
                mo_dict, vals = self._prepare_mo_dict(fiscalyear)
                # Update it
                for plan in phase.phase_plan_ids.filtered(
                        lambda l: l.fiscalyear_id.id == fiscalyear.id):
                    period = plan.calendar_period_id.period_id
                    month = int(period.date_start[5:7])
                    vals[mo_dict[month]] = plan.amount_plan
                sync.sync_budget_line_id.write(vals)
                # Mark synced
                sync.write({'synced': True,
                            'last_sync': fields.Datetime.now()})
        return True

    @api.multi
    def action_sync_phase_to_budget_line(self):
        return self.sync_phase_to_budget_line(fiscalyear_ids=False)  # do all

    # Statuses
    @api.multi
    def action_submit(self):
        self.write({'state': 'submit'})

    @api.multi
    def action_approve(self):
        self.write({'state': 'approve'})

    @api.multi
    def action_reject(self):
        self.write({'state': 'reject'})

    @api.multi
    def action_delete(self):
        self.write({'state': 'delete'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_close(self):
        self.write({'state': 'close'})

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})


class ResInvestConstructionBudgetPlan(models.Model):
    _name = 'res.invest.construction.budget.plan'
    _description = 'Investment Construction Budget Plan'
    _order = 'fiscalyear_id'

    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='Fiscal Year',
        required=True,
        readonly=True,
    )
    invest_construction_id = fields.Many2one(
        'res.invest.construction',
        string='Investment Construction',
        index=True,
        ondelete='cascade',
    )
    amount_plan = fields.Float(
        string='Amount',
        required=True,
    )
    _sql_constraints = [
        ('construction_plan_uniq',
         'unique(invest_construction_id, fiscalyar_id)',
         'Fiscal year must be unique for a construction project!'),
    ]


class ResInvestConstructionPhasePlan(models.Model):
    _name = 'res.invest.construction.phase.plan'
    _description = 'Investment Construction Phase Plan'
    _order = 'calendar_period_id'

    calendar_period_id = fields.Many2one(
        'account.period.calendar',
        string='Calendar Period',
        required=True,
        readonly=True,
    )
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        related='calendar_period_id.period_id.fiscalyear_id',
        string='Fiscal Year',
        required=True,
        readonly=True,
        store=True,
    )
    invest_construction_phase_id = fields.Many2one(
        'res.invest.construction.phase',
        string='Investment Construction Phase',
        index=True,
        ondelete='cascade',
    )
    invest_construction_id = fields.Many2one(
        'res.invest.construction',
        string='Investment Construction',
        related='invest_construction_phase_id.invest_construction_id',
        store=True,
    )
    amount_plan = fields.Float(
        string='Amount',
        required=True,
    )


class ResInvestConstructionPhaseSync(models.Model):
    _name = 'res.invest.construction.phase.sync'
    _description = 'Investment Construction Phase Sync History'
    _order = 'fiscalyear_id'

    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='Fiscal Year',
        required=True,
        readonly=True,
    )
    phase_id = fields.Many2one(
        'res.invest.construction.phase',
        string='Phase',
        index=True,
        ondelete='cascade',
    )
    sync_budget_line_id = fields.Many2one(
        'account.budget.line',
        string='Budget Line Ref',
        index=True,
        ondelete='set null',
    )
    budget_id = fields.Many2one(
        'account.budget',
        related='sync_budget_line_id.budget_id',
        string='Budget Control',
        readonly=True,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        help="Latest syncing date/time",
    )
    synced = fields.Boolean(
        string='Synced',
        default=False,
        help="Checked when it is synced. Unchecked when phase is updated"
        "then it will be synced again",
    )
