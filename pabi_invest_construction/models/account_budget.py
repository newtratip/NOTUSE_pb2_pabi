# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import Warning as UserError


class AccountBudget(models.Model):
    _inherit = 'account.budget'

    construction_auto_sync = fields.Boolean(
        string='Auto Sync',
        default=True,
        help="Auto sync with construction phase plan as soon as "
        "related phase is updated"
    )

    @api.multi
    def sync_budget_invest_construction(self):
        """ This method pull the invest construction phase's paln and update
        this budget's line. It will update all m1-m12 as they were approved.
        After synced, the synced = True, and it won't be pulled again.
        When phase is updated, it will reset synced = False, and ready for sync
        """
        self.ensure_one()  # Make sure it is synced one by one
        if self.chart_view != 'invest_construction':
            raise UserError(_('Not an invest construction budget control'))
        # Find matched phases for this budget control
        Phase = self.env['res.invest.construction.phase']
        PhaseSync = self.env['res.invest.construction.phase.sync']
        BudgetLine = self.env['account.budget.line']
        phases = Phase.search([
            ('org_id', '=', self.org_id.id),
            ('state', '=', 'approve'),
        ])
        fiscalyear_id = self.fiscalyear_id.id
        for phase in phases:
            # If sync only 1 specific phase, passed from construction.phase
            if 'phase_id' in self._context and \
                    phase.id != self._context.get('phase_id'):
                continue
            # Create phase sync if not exists
            phase_sync = phase.sync_ids.filtered(
                lambda l: l.fiscalyear_id.id == fiscalyear_id)
            if not phase_sync:
                phase_sync = PhaseSync.create({
                    'phase_id': phase.id,
                    'fiscalyear_id': fiscalyear_id,
                    'last_sync': False,
                    'synced': False,
                })
            # Create budget control line if not exists
            if not phase_sync.sync_budget_line_id:
                budget_line = BudgetLine.search([
                    ('budget_id', '=', self.id),
                    ('invest_construction_phase_id', '=', phase.id),
                ])
                if budget_line:
                    phase_sync.sync_budget_line_id = budget_line[0]
                else:
                    ic = phase.invest_construction_id
                    budget_line_dict = {
                        'budget_id': self.id,
                        'org_id': self.org_id.id,
                        'fund_id': ic.fund_ids and ic.fund_ids[0].id or False,
                        'invest_construction_id': ic.id,
                        'invest_construction_phase_id': phase.id,
                    }
                    phase_sync.sync_budget_line_id = \
                        BudgetLine.create(budget_line_dict)
            phase.sync_phase_to_budget_line([fiscalyear_id])
        return True
