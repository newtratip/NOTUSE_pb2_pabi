# -*- coding: utf-8 -*-

from openerp import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.one
    @api.depends('acceptance_ids')
    def _count_acceptances(self):
        PWAcceptance = self.env['purchase.work.acceptance']
        acceptance = PWAcceptance.search([('order_id', '=', self.id)])
        self.count_acceptance = len(acceptance)

    fine_condition = fields.Selection(
        selection=[
            ('day', 'Day'),
            ('date', 'Date'),
        ],
        string='Fine Condition',
        default='day',
        required=True,
    )
    date_fine = fields.Date(
        string='Fine Date',
        default=fields.Date.today(),
    )
    fine_num_days = fields.Integer(
        string='No. of Days',
        default=15,
    )
    fine_rate = fields.Float(
        string='Fine Rate',
        required=True,
        default=0.0,
    )
    acceptance_ids = fields.One2many(
        'purchase.work.acceptance',
        'order_id',
        string='Acceptance',
        readonly=False,
    )
    count_acceptance = fields.Integer(
        string='Count Acceptance',
        compute="_count_acceptances",
        store=True,
    )

    @api.multi
    def acceptance_open(self):
        return {
            'name': _('Purchase Work Acceptance'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.work.acceptance',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('order_id', '=', "+str(self.id)+")]",
        }