# -*- coding: utf-8 -*-

{
    'name': "NSTDA :: PABI2 - Advance Dunning Report",
    'summary': "",
    'author': "Ecosoft",
    'website': "http://ecosoft.co.th",
    'category': 'Account',
    'version': '0.1.0',

    'description': """

Expense Related Reports
=======================

* Dunning Report

    """,
    'depends': [
        'pabi_hr_expense',
    ],
    'data': [
        # 'edi/email_templates_-1_days.xml',
        'edi/email_templates_0_days.xml',
        'edi/email_templates_5_days.xml',
        'edi/email_templates_10_days.xml',
        'security/ir.model.access.csv',
        'data/dunning_sequence.xml',
        'data/report_data.xml',
        'views/pabi_dunning_letter_view.xml',
    ],
    'demo': [
    ],
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
