# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models
from .chartfield import CHART_VIEW_FIELD, CHART_FIELDS, ChartField
from lxml import etree


class AccountBudget(ChartField, models.Model):
    _inherit = 'account.budget'

    budget_revenue_line_unit_base = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'revenue')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_expense_line_unit_base = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'expense')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    # --
    budget_revenue_line_project_base = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'revenue')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_expense_line_project_base = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'expense')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    # --
    budget_revenue_line_personnel = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'revenue')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_expense_line_personnel = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'expense')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    # --
    budget_revenue_line_invest_asset = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'revenue')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_expense_line_invest_asset = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'expense')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    # --
    budget_revenue_line_invest_construction = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'revenue')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_expense_line_invest_construction = fields.One2many(
        'account.budget.line',
        'budget_id',
        string='Budget Lines',
        domain=[('budget_method', '=', 'expense')],
        states={'done': [('readonly', True)]},
        copy=True,
    )
    budget_summary_expense_line_ids = fields.One2many(
        'budget.unit.summary',
        'budget_id',
        string='Summary by Activity Group',
        readonly=True,
        domain=[('budget_method', '=', 'expense')],
        help="Summary by Activity Group View",
    )
    budget_summary_revenue_line_ids = fields.One2many(
        'budget.unit.summary',
        'budget_id',
        string='Summary by Activity Group',
        readonly=True,
        domain=[('budget_method', '=', 'revenue')],
        help="Summary by Activity Group View",
    )
    cost_control_ids = fields.One2many(
        'budget.unit.job.order',
        'budget_id',
        string='Job Order',
        copy=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
    )

    @api.model
    def _get_budget_level_type_hook(self, budget):
        if 'chart_view' in budget and budget.chart_view:
            return budget.chart_view
        return super(AccountBudgetLine, self).\
            _get_budget_level_type_hook(budget)

    @api.multi
    def budget_validate(self):
        for budget in self:
            lines = budget.budget_line_ids
            for line in lines:
                res = line.\
                    _get_chained_dimension(CHART_VIEW_FIELD[budget.chart_view])
                line.write(res)
        # kittiu: Following might not necessary as we already split chart_view
        #         for budget in self:
        #             budget.validate_chartfields(budget.chart_view)
        #             lines = budget.budget_line_ids
        #             lines.validate_chartfields(budget.chart_view)
        return super(AccountBudget, self).budget_validate()

    @api.multi
    def budget_confirm(self):
        for budget in self:
            lines = budget.budget_line_ids
            for line in lines:
                res = line.\
                    _get_chained_dimension(CHART_VIEW_FIELD[budget.chart_view])
                line.write(res)
        # kittiu: Following might not necessary as we already split chart_view
        #         for budget in self:
        #             budget.validate_chartfields(budget.chart_view)
        #             lines = budget.budget_line_ids
        #             lines.validate_chartfields(budget.chart_view)
        return super(AccountBudget, self).budget_confirm()

    # TODO: When confirm budget, validate all fields has relationship

    @api.model
    def fields_view_get(self, view_id=None, view_type=False,
                        toolbar=False, submenu=False):
        res = super(AccountBudget, self).\
            fields_view_get(view_id=view_id, view_type=view_type,
                            toolbar=toolbar, submenu=submenu)
        FIELD_RELATION = {
            'unit_base': ['section_id',
                          'budget_revenue_line_unit_base',
                          'budget_expense_line_unit_base'],
            'project_base': ['program_id',
                             'budget_revenue_line_project_base',
                             'budget_expense_line_project_base'],
            'personnel': ['personnel_costcenter_id',
                          'budget_revenue_line_personnel',
                          'budget_expense_line_personnel'],
            'invest_asset': ['org_id',
                             'budget_revenue_line_invest_asset',
                             'budget_expense_line_invest_asset'],
            'invest_construction': ['org_id',
                                    'budget_revenue_line_invest_construction',
                                    'budget_expense_line_invest_construction'],
        }
        if self._context.get('default_chart_view', '') and view_type == 'form':
            budget_type = self._context['default_chart_view']
            del FIELD_RELATION[budget_type]
            doc = etree.XML(res['arch'])
            for key in FIELD_RELATION.keys():

                field_name = FIELD_RELATION[key][0]
                for node in doc.xpath("//field[@name='%s']" % field_name):
                    if (budget_type in ('invest_asset',
                                        'invest_construction') and
                            field_name == 'org_id'):
                        continue
                    node.getparent().remove(node)

                revenue_line_field_name = FIELD_RELATION[key][1]
                expense_line_field_name = FIELD_RELATION[key][2]
                node_lines = doc.xpath("//field[@name='%s']" %
                                       revenue_line_field_name)
                node_lines += doc.xpath("//field[@name='%s']" %
                                        expense_line_field_name)
                for node_line in node_lines:
                    node_line.getparent().remove(node_line)

            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def _get_past_actual_domain(self):
        self.ensure_one()
        dom = super(AccountBudget, self)._get_past_actual_domain()
        budget_type_dict = {
            'unit_base': 'section_id',
            'project_base': 'project_id',
            'personnel': 'personnel_costcenter_id',
            'invest_asset': 'investment_asset_id',
            'invest_construction': 'invest_construction_phase_id'}
        dimension = budget_type_dict[self.chart_view]
        dom.append((dimension, '=', self[dimension].id))
        return dom


class AccountBudgetLine(ChartField, models.Model):
    _inherit = 'account.budget.line'

    chart_view = fields.Selection(
        related='budget_id.chart_view',
        store=True,
    )
    item_id = fields.Many2one(
        'invest.asset.plan.item',
        string='Asset Info',
        ondelete='restrict',
        readonly=True,
        help="Special field to store Asset Item information",
    )
    display_name = fields.Char(
        string='Display Name',
        readonly=True,
        compute='_compute_display_name',
    )
    breakdown_line_id = fields.Many2one(
        'budget.unit.job.order.line',
        string='Breakdown Job Order Line ref.',
    )

    @api.model
    def _get_budget_level_type_hook(self, budget_line):
        if 'chart_view' in budget_line and budget_line.chart_view:
            return budget_line.chart_view
        return super(AccountBudgetLine, self).\
            _get_budget_level_type_hook(budget_line)

    @api.multi
    @api.depends()
    def _compute_display_name(self):
        for rec in self:
            if rec.activity_id:
                rec.display_name = rec.activity_id.name
                continue
            if rec.activity_group_id:
                rec.display_name = rec.activity_group_id.name
                continue
            for chartfield in CHART_FIELDS:
                if rec[chartfield[0]]:
                    rec.display_name = rec[chartfield[0]].name
                    break

    # === Project Base ===
    @api.onchange('program_id')
    def _onchange_program_id(self):
        r1 = self._onchange_focus_field(focus_field='program_id',
                                        parent_field='program_group_id',
                                        child_field='project_group_id')
        # Additionally, dommain for child project_id
        r2 = self._onchange_focus_field(focus_field='program_id',
                                        parent_field='program_group_id',
                                        child_field='project_id')
        res = {'domain': {}}
        res['domain'].update(r1['domain'])
        res['domain'].update(r2['domain'])
        return res

    @api.onchange('project_group_id')
    def _onchange_project_group_id(self):
        res = self._onchange_focus_field(focus_field='project_group_id',
                                         parent_field='program_group_id',
                                         child_field='project_id')
        return res

    @api.onchange('project_id')
    def _onchange_project_id(self):
        res = self._onchange_focus_field(focus_field='project_id',
                                         parent_field='project_group_id',
                                         child_field=False)
        return res

    # === Unit Base ===
    # Nohting for Unit Base, as Section already the lowest

    # === Invest Asset, Invest Construction ===
    @api.onchange('org_id')
    def _onchange_org_id(self):
        r1 = self._onchange_focus_field(focus_field='org_id',
                                        parent_field=False,
                                        child_field='invest_asset_id')
        r2 = self._onchange_focus_field(focus_field='org_id',
                                        parent_field=False,
                                        child_field='invest_construction_id')
        res = {'domain': {}}
        res['domain'].update(r1['domain'])
        res['domain'].update(r2['domain'])
        return res

    # === Personnel ===
    # Still unsure !!!
