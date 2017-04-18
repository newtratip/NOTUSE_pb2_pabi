# -*- coding: utf-8 -*-
{
    "name": "NSTDA :: PABI2 - Account",
    "summary": "",
    "version": "1.0",
    "category": "Accounting & Finance",
    "description": """

* Account posting by selected tax branch
* All WHT account post go to a selected tax branch
* History of partner's bank account changes. Only user set in company config
  will have right to approve.
* Payment Type (cheque, transfer)

    """,
    "website": "https://ecosoft.co.th/",
    "author": "Kitti U.",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "l10n_th_account",
        "l10n_th_account_tax_detail",
        "pabi_base",
        "pabi_chartfield",
        "pabi_account_move_document_ref",
        # "account_move_line_doc_ref",
        "hr_expense_auto_invoice",
        "pabi_source_document",
        "account_invoice_create_payment",
    ],
    "data": [
        "security/security_group.xml",
        "security/ir.model.access.csv",
        "wizard/approve_bank_account_wizard.xml",
        "wizard/print_wht_cert_wizard.xml",
        "views/account_view.xml",
        "views/account_config.xml",
        "views/account_voucher_view.xml",
        "views/account_invoice_view.xml",
        "views/voucher_payment_receipt_view.xml",
        "views/account_invoice_view.xml",
        "views/res_bank_view.xml",
        "views/res_partner_view.xml",
        "views/res_company_view.xml",
    ],
}
