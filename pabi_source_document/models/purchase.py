# -*- coding: utf-8 -*-
from openerp import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def action_invoice_create(self):
        invoice_id = super(PurchaseOrder, self).action_invoice_create()
        if invoice_id:
            for purchase in self:
                invoice = self.env['account.invoice'].browse(invoice_id)
                invoice.write({'source_document_id': '%s,%s'
                               % (self._model, purchase.id)})
        return invoice_id