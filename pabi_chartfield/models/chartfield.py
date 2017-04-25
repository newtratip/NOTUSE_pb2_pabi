# -*- coding: utf-8 -*-
from openerp import api, models, fields, _
from openerp.addons.pabi_base.models.res_common import ResCommon

from openerp.exceptions import ValidationError

# org -> sector -> subsector -> division -> *section* -> costcenter
#                                           (mission)
#
#      (type/tag)      (type/tag)   (type/tag)    (type/tag)     (type/tag)
#        (org)           (org)        (org)         (org)          (org)
# functional_area -> program_group -> program -> project_group -> *project*
#                                    (spa(s))                     (mission)
#
#    (section)
# personnel_costcenter
#
#    (org)
#   (invest_asset_categ)  # not dimension
# invest_asset
#
#        (org)
# invest_construction -> invest_construction_phase


def _loop_structure(res, rec, d, field, clear=False):
    """ Loop through CHART_STRUCTURE to get the chained data """

    if clear or (field not in rec):
        res.update({field: False})
    elif rec[field]:
        res.update({field: rec[field].id})

    for k, _dummy in d[field].iteritems():
        if isinstance(d, dict):
            if rec[field]:
                _loop_structure(res, rec[field], d[field], k, clear)
            else:
                _loop_structure(res, rec, d[field], k, clear)


CHART_STRUCTURE = \
    {
        'section_id': {
            'division_id': {
                'subsector_id': {
                    'sector_id': {
                        'org_id': {}
                    },
                },
            },
            'mission_id': {},
            'costcenter_id': {
                'taxbranch_id': {}
            },
        },
        'project_id': {
            'project_group_id': {
                'program_id': {
                    'program_group_id': {
                        'functional_area_id': {},
                        'org_id': {},
                        'tag_id': {
                            'tag_type_id': {}
                        },
                    },
                    'org_id': {},
                    'tag_id': {
                        'tag_type_id': {}
                    },
                },
                'org_id': {},
                'tag_id': {
                    'tag_type_id': {}
                },
            },
            'org_id': {},
            'tag_id': {
                'tag_type_id': {}
            },
            'mission_id': {},
            'costcenter_id': {
                'taxbranch_id': {}
            },
        },
        'personnel_costcenter_id': {
            'section_id': {
                'division_id': {
                    'subsector_id': {
                        'sector_id': {
                            'org_id': {}
                        },
                    },
                },
                'mission_id': {},
                'costcenter_id': {
                    'taxbranch_id': {}
                },
            },
        },
        'invest_asset_id': {
            'costcenter_id': {
                'taxbranch_id': {}
            },
            'org_id': {},
        },
        'invest_construction_phase_id': {
            'invest_construction_id': {
                'costcenter_id': {
                    'taxbranch_id': {}
                },
                'org_id': {},
            },
        },
        'cost_control_id': {
            'cost_control_type_id': {},
        },
        'fund_id': {}
    }


# Budget structure and its selection field in document)
# Only following field will be visible for selection
# Only 1 field in a group can exists together
CHART_SELECT = [
    'section_id',  # Binding
    'project_id',
    'personnel_costcenter_id',
    'invest_asset_id',
    'invest_construction_phase_id',
    'cost_control_id',  # Non-Binding
]

# All types of budget structure
# This is related to chart structure
CHART_VIEW = {
    'unit_base': ('Unit Based', 'section_id'),
    'project_base': ('Project Based', 'project_id'),
    'personnel': ('Personnel', 'personnel_costcenter_id'),
    'invest_asset': ('Investment Asset', 'invest_asset_id'),
    'invest_construction': ('Investment Construction',
                            'invest_construction_id'),
}

CHART_VIEW_LIST = [(x[0], x[1][0]) for x in CHART_VIEW.items()]
CHART_VIEW_FIELD = dict([(x[0], x[1][1]) for x in CHART_VIEW.items()])

# For verification, to ensure that no field is valid outside of its view
CHART_FIELDS = [
    ('spa_id', ['project_base']),
    ('mission_id', ['project_base',
                    'unit_base',
                    'personnel',
                    ]),  # both
    ('tag_type_id', ['project_base']),
    ('tag_id', ['project_base']),
    # Project Based
    ('functional_area_id', ['project_base']),
    ('program_group_id', ['project_base']),
    ('program_id', ['project_base']),
    ('project_group_id', ['project_base']),
    ('project_id', ['project_base']),
    # Unit Based
    ('org_id', ['unit_base',
                'project_base',
                'personnel',
                'invest_asset',
                'invest_construction',
                ]),  # All
    ('sector_id', ['unit_base',
                   'personnel',
                   ]),
    ('subsector_id', ['unit_base',
                      'personnel',
                      ]),
    ('division_id', ['unit_base',
                     'personnel',
                     ]),
    ('section_id', ['unit_base',
                    'personnel',
                    ]),
    ('costcenter_id', ['unit_base',
                       'personnel',
                       ]),
    ('taxbranch_id', ['unit_base',
                      'project_base',
                      'personnel',
                      ]),
    # Personnel
    ('personnel_costcenter_id', ['personnel']),
    # Investment
    # - Asset
    ('invest_asset_id', ['invest_asset']),
    # - Construction
    ('invest_construction_id', ['invest_construction']),
    ('invest_construction_phase_id', ['invest_construction']),
    # Non Binding
    ('cost_control_type_id', ['unit_base',
                              'project_base',
                              'personnel',
                              ]),
    ('cost_control_id', ['unit_base',
                         'project_base',
                         'personnel',
                         ]),
    ('fund_id', ['unit_base',
                 'project_base',
                 'personnel',
                 'invest_asset',
                 'invest_construction',
                 ]),
]


# Extra non-binding chartfield (similar to activity)
class CostControlType(ResCommon, models.Model):
    _name = 'cost.control.type'
    _description = 'Job Order Type'

    description = fields.Text(
        string='Description',
    )


class CostControl(ResCommon, models.Model):
    _name = 'cost.control'
    _inherit = ['mail.thread']
    _description = 'Job Order'

    @api.model
    def _get_owner_level_selection(self):
        selection = [
            ('org', 'Org'),
            ('sector', 'Sector'),
            ('subsector', 'Subsector'),
            ('division', 'Division'),
            ('section', 'Section'),
        ]
        return selection

    description = fields.Text(
        string='Description',
    )
    cost_control_type_id = fields.Many2one(
        'cost.control.type',
        string='Job Order Type',
        required=True,
        track_visibility='onchange',
    )
    public = fields.Boolean(
        string="NSTDA Wide",
        copy=False,
        default=True,
        track_visibility='onchange',
    )
    owner_level = fields.Selection(
        string="Owner Level",
        selection=_get_owner_level_selection,
        copy=False,
        track_visibility='onchange',
    )
    # Unit Base
    org_id = fields.Many2one(
        'res.org',
        string='Org',
        track_visibility='onchange',
    )
    sector_id = fields.Many2one(
        'res.sector',
        string='Sector',
        track_visibility='onchange',
    )
    subsector_id = fields.Many2one(
        'res.subsector',
        string='Subsector',
        track_visibility='onchange',
    )
    division_id = fields.Many2one(
        'res.division',
        string='Division',
        track_visibility='onchange',
    )
    section_id = fields.Many2one(
        'res.section',
        string='Section',
        track_visibility='onchange',
    )
    active = fields.Boolean(
        track_visibility='onchange',
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Job Order Name must be unique!'),
    ]

    @api.model
    def _check_access(self):
        if not self.env.user.has_group(
                'pabi_base.group_cooperate_budget')\
            and not self.env.user.has_group(
                'pabi_base.group_operating_unit_budget'):
            raise ValidationError(
                _('Sorry! \n You are not authorized to edit this field.'))
        return True

    @api.model
    def create(self, vals):
        if 'public' in vals:
            self._check_access()
        return super(CostControl, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'public' in vals:
            self._check_access()
        return super(CostControl, self).write(vals)

    @api.onchange('public')
    def _onchange_public(self):
        self.owner_level = False
        self.org_id = False
        self.sector_id = False
        self.subsector_id = False
        self.division_id = False
        self.section_id = False

    @api.onchange('owner_level')
    def _onchange_owner_level(self):
        self.org_id = False
        self.sector_id = False
        self.subsector_id = False
        self.division_id = False
        self.section_id = False

    # @api.multi
    # def name_get(self):
    #     result = []
    #     for cc in self:
    #         result.append(
    #             (cc.id,
    #              "%s / %s" % (cc.cost_control_type_id.name or '-',
    #                           cc.name or '-')))
    #     return result


class HeaderTaxBranch(object):

    taxbranch_ids = fields.Many2many(
        'res.taxbranch',
        string='Tax Branches',
        help="This field store available taxbranch of this document",
    )
    len_taxbranch = fields.Integer(
        string='Len Tax Branches',
        help="Special field, used just to set field as Tax Branch required",
    )
    taxbranch_id = fields.Many2one(
        'res.taxbranch',
        string='Tax Branch',
        domain="[('id', 'in', taxbranch_ids and "
        "taxbranch_ids[0] and taxbranch_ids[0][2] or False)]",
    )

    def _set_taxbranch_ids(self, lines):
        taxbranch_ids = list(set([x.taxbranch_id.id
                                  for x in lines if x.taxbranch_id]))
        if not taxbranch_ids:  # If not tax branch at all, allow manual select
            taxbranch_ids = self.env['res.taxbranch'].search([]).ids
        self.taxbranch_ids = taxbranch_ids
        self.len_taxbranch = len(taxbranch_ids)

    def _set_header_taxbranch_id(self):
        if len(self.taxbranch_ids) == 1:
            self.taxbranch_id = self.taxbranch_ids[0]
        if len(self.taxbranch_ids) > 1 and not self.taxbranch_id:
            self.taxbranch_id = False
        # For advance invoice, it is possible to have taxbranch_id this way
        # if len(self.taxbranch_ids) == 0:
        #     self.taxbranch_id = False

    @api.multi
    def write(self, vals):
        res = super(HeaderTaxBranch, self).write(vals)
        if self.env.context.get('MyModelLoopBreaker'):
            return res
        self = self.with_context(MyModelLoopBreaker=True)
        for rec in self:
            rec._set_header_taxbranch_id()
        return res


class ChartField(object):

    # Project Base
    spa_id = fields.Many2one(
        'res.spa',
        string='SPA',
        default=lambda self: self.env['res.spa'].
        browse(self._context.get('spa_id')),
    )
    mission_id = fields.Many2one(
        'res.mission',
        string='Mission',
        default=lambda self: self.env['res.mission'].
        browse(self._context.get('mission_id')),
    )
    tag_type_id = fields.Many2one(
        'res.tag.type',
        string='Tag Type',
        default=lambda self: self.env['res.tag.type'].
        browse(self._context.get('tag_type_id')),
    )
    tag_id = fields.Many2one(
        'res.tag',
        string='Tag',
        default=lambda self: self.env['res.tag'].
        browse(self._context.get('tag_id')),
    )
    functional_area_id = fields.Many2one(
        'res.functional.area',
        string='Functional Area',
        default=lambda self: self.env['res.functional.area'].
        browse(self._context.get('functional_area_id')),
    )
    program_group_id = fields.Many2one(
        'res.program.group',
        string='Program Group',
        default=lambda self: self.env['res.program.group'].
        browse(self._context.get('program_group_id')),
    )
    program_id = fields.Many2one(
        'res.program',
        string='Program',
        default=lambda self: self.env['res.program'].
        browse(self._context.get('program_id')),
    )
    project_group_id = fields.Many2one(
        'res.project.group',
        string='Project Group',
        default=lambda self: self.env['res.project.group'].
        browse(self._context.get('project_group_id')),
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        default=lambda self: self.env['res.project'].
        browse(self._context.get('project_id')),
    )
    fund_id = fields.Many2one(
        'res.fund',
        string='Fund',
    )
    # Unit Base
    org_id = fields.Many2one(
        'res.org',
        string='Org',
        default=lambda self: self.env['res.org'].
        browse(self._context.get('org_id')),
    )
    sector_id = fields.Many2one(
        'res.sector',
        string='Sector',
        default=lambda self: self.env['res.sector'].
        browse(self._context.get('sector_id')),
    )
    subsector_id = fields.Many2one(
        'res.subsector',
        string='Subsector',
        default=lambda self: self.env['res.subsector'].
        browse(self._context.get('subsector_id')),
    )
    division_id = fields.Many2one(
        'res.division',
        string='Division',
        default=lambda self: self.env['res.division'].
        browse(self._context.get('division_id')),
    )
    section_id = fields.Many2one(
        'res.section',
        string='Section',
        default=lambda self: self.env['res.section'].
        browse(self._context.get('section_id')),
    )
    costcenter_id = fields.Many2one(
        'res.costcenter',
        string='Costcenter',
        default=lambda self: self.env['res.costcenter'].
        browse(self._context.get('costcenter_id')),
    )
    taxbranch_id = fields.Many2one(
        'res.taxbranch',
        string='Tax Branch',
        default=lambda self: self.env['res.taxbranch'].
        browse(self._context.get('taxbranch_id')),
    )
    # Personnel
    personnel_costcenter_id = fields.Many2one(
        'res.personnel.costcenter',
        string='Personnel Budget',
        default=lambda self: self.env['res.personnel.costcenter'].
        browse(self._context.get('personnel_costcenter_id')),
    )
    # Investment - Asset
    invest_asset_id = fields.Many2one(
        'res.invest.asset',
        string='Investment Asset',
        default=lambda self: self.env['res.invest.asset'].
        browse(self._context.get('invest_asset_id')),
    )
    # Investment - Construction
    invest_construction_id = fields.Many2one(
        'res.invest.construction',
        string='Construction',
    )
    invest_construction_phase_id = fields.Many2one(
        'res.invest.construction.phase',
        string='Construction Phase',
        default=lambda self: self.env['res.invest.construction.phase'].
        browse(self._context.get('invest_construction_id')),
    )
    # Non Binding Dimension
    cost_control_id = fields.Many2one(
        'cost.control',
        string='Job Order',
        default=lambda self: self.env['cost.control'].
        browse(self._context.get('cost_control_id')),
    )
    cost_control_type_id = fields.Many2one(
        'cost.control.type',
        string='Job Order Type',
        default=lambda self: self.env['cost.control.type'].
        browse(self._context.get('cost_control_type_id')),
    )
    chart_view = fields.Selection(
        CHART_VIEW_LIST,
        string='Budget View',
        required=False,
        copy=True,
    )

    # Required fields (to ensure no error onchange)
    activity_id = fields.Many2one('account.activity')
    product_id = fields.Many2one('product.product')
    account_id = fields.Many2one('account.account')

    @api.model
    def _get_fund_domain(self):
        domain_str = """
            ['|', '|', '|', '|',
            ('project_ids', 'in', [project_id or -1]),
            ('section_ids', 'in', [section_id or -1]),
            ('invest_asset_ids', 'in', [invest_asset_id or -1]),
            ('invest_construction_phase_ids', 'in',
                [invest_construction_phase_id or -1]),
            ('personnel_costcenter_ids', 'in',
                [personnel_costcenter_id or -1])]
        """
        return domain_str

    @api.multi
    def validate_chartfields(self, chart_type):
        # Only same chart type as specified will remains
        for line in self:
            for d in CHART_FIELDS:
                if chart_type not in d[1]:
                    line[d[0]] = False

    @api.model
    def _get_chained_dimension(self, field, clear=False):
        """ This method will use CHART_STRUCTURE to prepare data """
        res = {}
        _loop_structure(res, self, CHART_STRUCTURE, field, clear=clear)
        if field in res:
            res.pop(field)  # To avoid recursive
        return res

    @api.model
    def _get_default_fund(self):
        # If that dimension have 1 funds, use that fund.
        # If that dimension have no funds, use NSTDA
        # Else return false
        fund_id = False
        funds = False
        if self.project_id:
            funds = self.project_id.fund_ids
        if self.section_id:
            funds = self.section_id.fund_ids
        if self.personnel_costcenter_id:
            funds = self.personnel_costcenter_id.fund_ids
        if self.invest_asset_id:
            funds = self.invest_asset_id.fund_ids
        if self.invest_construction_phase_id:
            funds = self.invest_construction_phase_id.fund_ids
        # Get default fund
        if len(funds) == 1:
            fund_id = funds[0].id
        else:
            fund_id = False
        return fund_id

    # Section
    @api.onchange('section_id')
    def _onchange_section_id(self):
        if self.section_id:
            if 'project_id' in self:
                self.project_id = False
            if 'personnel_costcenter_id' in self:
                self.personnel_costcenter_id = False
            if 'invest_asset_id' in self:
                self.invest_asset_id = False
            if 'invest_construction_phase_id' in self:
                self.invest_construction_phase_id = False
            self.fund_id = self._get_default_fund()

    # Project Base
    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            if 'section_id' in self:
                self.section_id = False
            if 'personnel_costcenter_id' in self:
                self.personnel_costcenter_id = False
            if 'invest_asset_id' in self:
                self.invest_asset_id = False
            if 'invest_construction_phase_id' in self:
                self.invest_construction_phase_id = False
            self.fund_id = self._get_default_fund()

    # Personnel
    @api.onchange('personnel_costcenter_id')
    def _onchange_personnel_costcenter_id(self):
        if self.personnel_costcenter_id:
            if 'section_id' in self:
                self.section_id = False
            if 'project_id' in self:
                self.project_id = False
            if 'invest_asset_id' in self:
                self.invest_asset_id = False
            if 'invest_construction_phase_id' in self:
                self.invest_construction_phase_id = False
            self.fund_id = self._get_default_fund()

    # Investment Asset
    @api.onchange('invest_asset_id')
    def _onchange_invest_asset_id(self):
        if self.invest_asset_id:
            if 'section_id' in self:
                self.section_id = False
            if 'project_id' in self:
                self.project_id = False
            if 'personnel_costcenter_id' in self:
                self.personnel_costcenter_id = False
            if 'invest_construction_phase_id' in self:
                self.invest_construction_phase_id = False
            self.fund_id = self._get_default_fund()

    # Investment Construction
    @api.onchange('invest_construction_phase_id')
    def _onchange_invest_construction_phase_id(self):
        if self.invest_construction_phase_id:
            if 'section_id' in self:
                self.section_id = False
            if 'project_id' in self:
                self.project_id = False
            if 'invest_asset_id' in self:
                self.invest_asset_id = False
            if 'personnel_costcenter_id' in self:
                self.personnel_costcenter_id = False
            self.fund_id = self._get_default_fund()

    @api.multi
    def update_related_dimension(self, vals):
        # Find selected dimension that is in CHART_SELECT list
        selects = list(set(CHART_SELECT) & set(vals.keys()))
        if selects:
            selects = dict([(x, vals[x]) for x in selects])
            selects_no = {k: v for k, v in selects.items() if not v}
            selects_yes = {k: v for k, v in selects.items() if v}
            # update value = false first, the sequence is important
            res = {}
            for field, _dummy in selects_no.items():
                res.update(self._get_chained_dimension(field, clear=True))
            # res.update({'chart_view': self._get_chart_view(selects_yes)})
            for field, _dummy in selects_yes.items():
                if field in res:
                    res.pop(field)
                res.update(self._get_chained_dimension(field))
            self.with_context(MyModelLoopBreaker=True).write(res)


class ChartFieldAction(ChartField):
    """ Chartfield + Onchange for Document Transaction
        1) No Filter Domain from 1 field to another. Free to choose
        2) Choosing only folloiwng fields will auto populate others
            - const_control_id (extra)
            - section_id
            - project_id
            - personnel_costcenter_id
            - invest_asset_id
            - invest_construction_id
    """

    chart_view = fields.Selection(
        CHART_VIEW_LIST,
        compute='_compute_chart_view',
        store=True,
    )
    require_chartfield = fields.Boolean(
        string='Require Chartfield',
        compute='_compute_require_chartfield',
    )
    fund_id = fields.Many2one(
        domain=lambda self: self._get_fund_domain(),
    )

    @api.multi
    @api.depends('project_id', 'section_id', 'personnel_costcenter_id',
                 'invest_asset_id', 'invest_construction_id')
    def _compute_chart_view(self):
        for rec in self:
            rec.chart_view = False
            view_set = False
            for k, v in CHART_VIEW_FIELD.items():
                if rec[v] and not view_set:
                    if not view_set:
                        rec.chart_view = k
                        view_set = True
                    else:
                        raise ValidationError(
                            _('More than 1 dimension selected'))

    @api.multi
    @api.depends('activity_id', 'account_id')
    def _compute_require_chartfield(self):
        for rec in self:
            account = False
            is_alyt_line = rec._name in ('account.analytic.line')  # Special
            if not is_alyt_line and 'account_id' in rec and rec.account_id:
                account = rec.account_id
            elif is_alyt_line and 'general_account_id' in rec \
                    and rec.general_account_id:
                account = rec.general_account_id
            elif 'activity_id' in rec and rec.activity_id:
                account = rec.activity_id.account_id
            if account:
                report_type = account.user_type.report_type
                rec.require_chartfield = report_type not in ('asset',
                                                             'liability')
            else:
                rec.require_chartfield = True
            if not rec.require_chartfield:
                rec.section_id = False
                rec.project_id = False
                rec.personnel_costcenter_id = False
                rec.invest_asset_id = False
                rec.invest_construction_phase_id = False
        return

    @api.multi
    def write(self, vals):
        # For balance sheet account, alwasy set no dimension
        if vals.get('account_id', False):
            account = self.env['account.account'].browse(vals['account_id'])
            if account.user_type.report_type in ('asset', 'liability'):
                vals['section_id'] = False
                vals['project_id'] = False
                vals['personnel_costcenter_id'] = False
                vals['invest_asset_id'] = False
                vals['invest_construction_phase_id'] = False
        res = super(ChartFieldAction, self).write(vals)
        if not self._context.get('MyModelLoopBreaker', False):
            self.update_related_dimension(vals)
        return res
