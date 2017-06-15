# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class AccountAssetTransfer(models.Model):
    _name = 'account.asset.transfer'
    _description = 'Transfer types - 1. Change Owner 2. New Asset'
    _order = 'name desc'

    name = fields.Char(
        string='Name',
        default='/',
        required=True,
        readonly=True,
        copy=False,
    )
    date = fields.Date(
        string='Date',
        default=lambda self: fields.Date.context_today(self),
        required=True,
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    user_id = fields.Many2one(
        'res.users',
        string='Prepared By',
        default=lambda self: self.env.user,
        required=True,
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    note = fields.Text(
        string='Note',
        copy=False,
    )
    transfer_type = fields.Selection(
        [('new_asset', 'New Asset'),
         ('change_owner', 'Change Owner')],
        string='Transfer Type',
        default='new_asset',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    # To Asset Type
    product_id = fields.Many2one(
        'product.product',
        string='To Asset Type',
        domain=[('asset', '=', True)],
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    asset_name = fields.Char(
        string='Asset Name',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    asset_category_id = fields.Many2one(
        'account.asset.category',
        related='product_id.asset_category_id',
        string='To Asset Category',
        store=True,
        readonly=True,
    )
    ref_asset_id = fields.Many2one(
        'account.asset.asset',
        string='Asset Created',
        readonly=True,
        copy=False,
    )
    # To New Owner
    section_id = fields.Many2one(
        'res.section',
        string='Section',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    costcenter_id = fields.Many2one(
        'res.costcenter',
        string='Costcenter',
        compute='_compute_costcenter_id',
    )
    transfer_asset_ids = fields.Many2many(
        'account.asset.asset',
        'account_asset_asset_transfer_rel',
        'transfer_id', 'asset_id',
        string='Assets to Transfer',
        domain=[('type', '!=', 'view')],
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('done', 'Transferred'),
         ('cancel', 'Cancelled')],
        string='Status',
        default='draft',
        readonly=True,
        copy=False,
    )
    # For search criteria
    search_normal_asset = fields.Boolean(
        string='Search Normal Asset',
        default=False,
        readonly=True,
    )
    search_no_depre_asset = fields.Boolean(
        string='Search No Depre. Asset',
        default=False,
        readonly=True,
    )

    @api.onchange('transfer_type')
    def _onchange_transfer_type(self):
        self.search_normal_asset = False
        self.search_no_depre_asset = False
        if self.transfer_type == 'new_asset':
            self.search_no_depre_asset = True
        if self.transfer_type == 'change_owner':
            self.search_normal_asset = True

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.asset_name = self.product_id.name

    @api.onchange('project_id', 'section_id')
    def _onchange_project_section(self):
        if self.project_id:
            self.section_id = False
        if self.section_id:
            self.project_id = False

    @api.multi
    @api.depends('project_id', 'section_id')
    def _compute_costcenter_id(self):
        for rec in self:
            if rec.project_id or rec. section_id:
                rec.costcenter_id = rec.project_id.costcenter_id or \
                    rec.section_id.costcenter_id

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].\
                get('account.asset.transfer') or '/'
        return super(AccountAssetTransfer, self).create(vals)

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_done(self):
        for rec in self:
            if rec.transfer_type == 'new_asset':
                rec._transfer_new_asset()
            if rec.transfer_type == 'change_owner':
                rec._transfer_change_owner()
        self.write({'state': 'done'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def _transfer_new_asset(self):
        """ The Concept
        * A new asset will be created, owner chartfields will be the same
          * So, make sure that the asset_category_id only on new move
        * All source asset must have same owner chartfields, otherwise, warning
        * We code to allow transfering the asset with depre, in fact, it won't
        * Inactive source assets
        Accoun Moves
        ============
        Dr Accumulated depreciation of transfer assets (for each asset, if any)
            Cr Asset Value of trasferring assets (for each asset)
        Dr Asset Value to the new asset
            Cr Accumulated Depreciation of to the new asset (if any)
        """
        self.ensure_one()
        AccountMove = self.env['account.move']
        Asset = self.env['account.asset.asset']
        Period = self.env['account.period']
        period = Period.find()
        # For Transfer: Property of New Asset
        new_product = self.product_id
        new_asset_category = new_product.asset_category_id
        new_journal = new_asset_category.journal_id
        new_account_asset = new_asset_category.account_asset_id
        # Owner
        project = self.transfer_asset_ids.mapped('project_id')
        section = self.transfer_asset_ids.mapped('section_id')
        # For Transfer, all asset must belong to same owner
        if len(project) > 1 or len(section) > 1:
            raise ValidationError(
                _('When transfer to new asset, all selected '
                  'assets must belong to same owner!'))
        # Prepare Old Move
        move_lines = []
        asset_move_lines_dict, depre_move_lines_dict = \
            Asset._prepare_asset_reverse_moves(self.transfer_asset_ids)
        move_lines += asset_move_lines_dict + depre_move_lines_dict
        # For transfer case, we first want to make sure that asset_id is false
        for x in move_lines:
            x.update({'asset_id': False})
        # Create move line for target asset
        # Asset
        new_asset_move_line_dict = \
            Asset._prepare_asset_target_move(asset_move_lines_dict)
        # For transfer, create a new asset by update following fields
        new_asset_move_line_dict.update({
            'name': self.asset_name,
            'product_id': new_product.id,
            'asset_category_id': new_asset_category.id,
            'account_id': new_account_asset.id,
        })
        move_lines.append(new_asset_move_line_dict)
        # Depre
        if depre_move_lines_dict:
            new_depre_move_lines_dict = \
                Asset._prepare_asset_target_move(depre_move_lines_dict)
            move_lines.append(new_depre_move_lines_dict)
        # Finalize all moves before create it.
        final_move_lines = [(0, 0, x) for x in move_lines]
        move_dict = {'journal_id': new_journal.id,
                     'line_id': final_move_lines,
                     'period_id': period.id,
                     'date': fields.Date.context_today(self),
                     'ref': self.name}
        move = AccountMove.create(move_dict)
        # For transfer, new asset should be created
        asset = move.line_id.mapped('asset_id')
        if len(asset) != 1:
            raise ValidationError(
                _('An asset should be created, something is wrong!'))
        self.ref_asset_id = asset.id
        asset.source_asset_ids = self.transfer_asset_ids
        self.transfer_asset_ids.write({'active': False,
                                       'target_asset_id': asset.id,
                                       })