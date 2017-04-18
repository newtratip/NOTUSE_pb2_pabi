# -*- coding: utf-8 -*-
{
    'name': 'Account Move - Adjustment Types',
    'version': '8.0.1.0.0',
    'author': 'Ecosoft',
    'summary': 'Journal Entries Adjustmnet Doctypes',
    'description': """

New Menus

* Journal Adj.Bud.
* Journal Adj.No.Bud.

Note: following are arequiremen for system to properly create analytic line

1. journal line must choose account of user type = Profit & Loss
2. journal line must have analytic account
    (which is normally auto created if Product/Activity selected)
3. journal must have analytic journal, otherwise warning will show.

    """,
    'category': 'Accounting',
    'website': 'http://www.ecosoft.co.th',
    'images': [],
    'depends': [
        'account_subscription_enhanced',
        'pabi_account_move_document_ref',
    ],
    'demo': [],
    'data': [
        'data/journal_data.xml',
        'views/account_view.xml',
    ],
    'test': [
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
