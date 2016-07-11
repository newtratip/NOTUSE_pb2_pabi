# -*- coding: utf-8 -*-
from openerp import models, api, _

""" This class is intended for Web Service call to/from Alfresco """


class HRExpense(models.Model):
    _inherit = 'hr.expense.expense'

    @api.model
    def test_generate_hr_expense_advance(self):
        data_dict = {
            'is_employee_advance': u'True',
            'number': u'/',  # av_id
            'employee_code': u'004012',  # request for employee
            'date': u'2016-01-31',  # by_time
            'write_date': u'2016-01-31 00:00:00',  # updated_time
            'advance_type': u'attend_seminar',  # or by_product, objective_type
            'date_back': u'2016-10-30',  # cost_control_to
            'name': u'Object of this Advance',  # objective
            'apweb_ref_url': u'',
            'line_ids': [  # 1 line only, Advance
                {
                 'is_advance_product_line': u'True',
                 'name': u'Employee Advance',  # Expense Note (not in AF?)
                 'unit_amount': u'2000',  # total
                 'cost_control_id.id': u'',
                 },
                {
                 'is_advance_product_line': u'True',
                 'name': u'Employee Advance 2',  # Expense Note (not in AF?)
                 'unit_amount': u'3000',  # total
                 'cost_control_id.id': u'',
                 },
            ],
            'attendee_employee_ids': [
                {
                 'employee_code': u'000143',
                 'position_id.id': u'',
                 },
                {
                 'employee_code': u'000165',
                 'position_id.id': u'',
                 },
                {
                 'employee_code': u'000166',
                 'position_id.id': u'',
                 },
                {
                 'employee_code': u'000177',
                 'position_id.id': u'',
                 },
            ],
            'attendee_external_ids': [
                {
                 'attendee_name': u'Walai Charoenchaimongkol',
                 'position': u'Manager',
                 },
            ],
            'attachment_ids': [
                {
                 'name': u'Expense1.pdf',
                 'description': u'My Expense 1 Document Description',
                 'url': u'b1d1d9a9-740f-42ad-a96b-b4747edbae1d',
                 },
                {
                 'name': u'Expense2.pdf',
                 'description': u'My Expense 2 Document Description',
                 'url': u'b1d1d9a9-740f-42ad-a96b-b4747edbae1d',
                 },
            ]
        }
        return self.generate_hr_expense(data_dict)

    @api.model
    def _pre_process_hr_expense(self, data_dict):
        Employee = self.env['hr.employee']
        # employee_code to employee_id.idย
        domain = [('employee_code', '=', data_dict.get('employee_code'))]
        employee = Employee.search(domain)
        data_dict['employee_id.id'] = employee.id
        del data_dict['employee_code']
        # OU based on employee
        data_dict['operating_unit_id.id'] = \
            employee.org_id.operating_unit_id.id
        # Advance product
        if 'line_ids' in data_dict:
            advance_product = self.env.ref('hr_expense_advance_clearing.'
                                           'product_product_employee_advance')
            for data in data_dict['line_ids']:
                data['product_id.id'] = advance_product.id
                data['uom_id.id'] = advance_product.uom_id.id
        # attendee's employee_code
        if 'attendee_employee_ids' in data_dict:
            for data in data_dict['attendee_employee_ids']:
                domain = [('employee_code', '=', data.get('employee_code'))]
                data['employee_id.id'] = Employee.search(domain).id
                del data['employee_code']
        # attachment
        if 'attachment_ids' in data_dict:
            for data in data_dict['attachment_ids']:
                ConfParam = self.env['ir.config_parameter']
                file_prefix = ConfParam.get_param('pabiweb_file_prefix')
                data['url'] = file_prefix + data['url']
                data['res_model'] = self._name
                data['type'] = 'url'
        return data_dict

    @api.model
    def _post_process_hr_expense(self, res):
        # Submit to manager
        expense = self.env['hr.expense.expense'].browse(res['result']['id'])
        expense.signal_workflow('confirm')
        return res

    @api.model
    def generate_hr_expense(self, data_dict):
        try:
            # Start
            data_dict = self._pre_process_hr_expense(data_dict)
            res = self._create_hr_expense_expense(data_dict)
            if res['is_success'] is True:
                self._post_process_hr_expense(res)
            # End
            self._cr.commit()
        except Exception, e:
            res = {
                'is_success': False,
                'result': False,
                'messages': e,
            }
            self._cr.rollback()
        return res

    @api.model
    def _finalize_data_to_load(self, data_dict):
        """
        This method will convert user friendly data_dict
        to load() compatible fields/data
        Currently it is working with multiple line table but with 1 level only
        data_dict = {
            'name': 'ABC',
            'line_ids': ({'desc': 'DESC'},),
            'line2_ids': ({'desc': 'DESC'},),
        }
        to
        fields = ['name', 'line_ids/desc', 'line2_ids/desc']
        data = [('ABC', 'DESC', 'DESC')]
        """
        fields = data_dict.keys()
        data = data_dict.values()
        line_count = 1
        _table_fields = []  # Tuple fields
        for key in fields:
            if isinstance(data_dict[key], list) or \
                    isinstance(data_dict[key], tuple):
                _table_fields.append(key)
        data_array = {}
        for table in _table_fields:
            data_array[table] = False
            data_array[table+'_fields'] = False
            if table in fields:
                i = fields.index(table)
                data_array[table] = data[i] or ()  # ({'x': 1, 'y': 2}, {})
                del fields[i]
                del data[i]
                line_count = max(line_count, len(data_array[table]))
            if data_array[table]:
                data_array[table+'_fields'] = \
                    [table+'/'+key for key in data_array[table][0].keys()]
            fields += data_array[table+'_fields']
        # Data
        datas = []
        for i in range(0, line_count, 1):
            record = []
            for table in _table_fields:
                data_array[table+'_data'] = False
                if data_array[table+'_fields']:
                    data_array[table+'_data'] = \
                        (len(data_array[table]) > i and data_array[table][i] or
                         {key: False for key in data_array[table+'_fields']})
                record += data_array[table+'_data'].values()
            if i == 0:
                datas += [tuple(data + record)]
            else:
                datas += [tuple([False for _x in data] + record)]
        return fields, datas

    @api.model
    def _create_hr_expense_expense(self, data_dict):
        res = {}
        # Final Preparation of fields and data
        fields, data = self._finalize_data_to_load(data_dict)
        load_res = self.load(fields, data)
        res_id = load_res['ids'] and load_res['ids'][0] or False
        if not res_id:
            res = {
                'is_success': False,
                'result': False,
                'messages': [m['message'] for m in load_res['messages']],
            }
        else:
            res = {
                'is_success': True,
                'result': {
                    'id': res_id,
                },
                'messages': _('Document created successfully'),
            }
        return res