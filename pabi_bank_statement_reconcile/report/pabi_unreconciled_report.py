# -*- coding: utf-8 -*-
from openerp import tools
from openerp import models


class PABIUnreconciledReport(models.Model):
    _name = 'pabi.unreconciled.report'
    _description = 'Account Tax Report (pdf/xls)'
    _auto = False

    # TODO: Add fields once report is confirmed

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            select a.id, a.name, a.report_type, a.match_method, a.date_report,
                a.doctype, a.payment_type, a.transfer_type, a.journal_id,
                a.account_id, a.date_from, a.date_to,
                b.statement_id, b.source, b.document,
                b.cheque_number, b.batch_code,
                b.date_value, b.amount, b.validate_user_id, b.days_outstanding,
                b.partner_code, b.partner_name,
                acct.code account_code, acct.name account_name,
                bank.bank_name, bank.acc_number bank_account_name,
                rp.name as validate_user
            from pabi_bank_statement a
            join
            (
                (select statement_id, 'bank' as source, document,
                    batch_code,
                    cheque_number, date_value, debit-credit as amount,
                    null as validate_user_id, null as days_outstanding,
                    partner_code, partner_name
                from pabi_bank_statement_import
                where match_item_id is null
                order by date_value, document, cheque_number)
            union
                (select statement_id, 'nstda' as source, document,
                    null as batch_code,
                    cheque_number, date_value, credit-debit as amount,
                    validate_user_id, days_outstanding,
                    partner_code, partner_name
                from pabi_bank_statement_item
                where match_import_id is null
                order by date_value, document, cheque_number)
            ) b
            on b.statement_id = a.id
            -- misc
            left outer join account_account acct
                on acct.id = a.account_id
            left outer join res_partner_bank bank
                on bank.journal_id = a.journal_id
            left outer join res_users usr
                on usr.id = b.validate_user_id
            left outer join res_partner rp on rp.id = usr.partner_id
        )""" % (self._table,)
        )
