# -*- coding: utf-8 -*-
from openerp import models, fields


class BudgetXlsOutput(models.TransientModel):

    _name = 'budget.xls.output'
    _description = 'Wizard to store the Excel output'

    xls_output = fields.Binary(string='Excel Output', readonly=True)
    name = fields.Char(string='File Name', help="Save report as .xls format")
