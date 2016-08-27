# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L.
# - Jordi Ballester Alomar
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models, _
from openerp.exceptions import Warning as UserError


class PurchaseRequestLineClose(models.TransientModel):
    _name = "purchase.request.line.close"
    _description = "Close Purchase Request Line"

    confirm_close = fields.Boolean(
        string='Confirm Closing Purchase Request Line'
    )

    @api.one
    def close_line(self):
        if not self.confirm_close:
            raise UserError(
                _("Can't close purchase request lines."
                  " Please check the confirm box.")
            )
        ReqLine = self.env['purchase.request.line']
        active_ids = self._context['active_ids']
        lines = ReqLine.search([('id', 'in', active_ids)])
        for line in lines:
            if line.state == 'close':
                raise UserError(
                    _("Can't close purchase request lines."
                      " Some lines are already closed.")
                )
            else:
                line.state = 'close'