# -*- coding: utf-8 -*-
# © 2016 Kitti U.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class ResDoctype(models.Model):
    _inherit = 'res.doctype'

    #   * Purchase Requisition
    #   * Work Acceptance
    #   * Approval Report
    #   * Stock Request
    #   * Stock Transfer
    #   * Stock Borrow
    #   * Payment Export
    #   * Bank Receipt
    #   * Interface Account

    refer_type = fields.Selection(
        selection_add=[
            ('purchase_requisition', 'Purchase Requisition'),
            ('work_acceptance', 'Work Acceptance'),
            ('approval_report', 'Approval Report'),
            ('stock_request', 'Stock Request'),
            ('stock_transfer', 'Stock Transfer'),
            ('stock_borrow', 'Stock Borrow'),
            ('payment_export', 'Payment Export'),
            ('bank_receipt', 'Bank Receipt'),
            ('interface_account', 'Interface Account'),
        ],
    )
