# -*- coding: utf-8 -*-

from openerp import fields, models


class StockRequest(models.Model):
    _inherit = "stock.request"

    reject_reason_txt = fields.Char(
        string="Rejected Reason",
        readonly=True,
    )
