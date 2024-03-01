import logging
from datetime import date

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.fields import Command


_logger = logging.getLogger(__name__)


class SaleYer(models.Model):
    _name = 'sale.yer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Year-end rebate"
    _order = 'id desc'

    name = fields.Char(
        string="YER Reference",
        required=True, copy=False, readonly=True,
        index='trigram',
        states={'draft': [('readonly', False)]},
        default=lambda self: _('New'))
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel')],
        compute='_compute_state',
        store=True, copy=False, index=True,
        tracking=3,
        default='draft'
    )
    domain = fields.Selection(selection=[
        ('company', 'Company'),
        ('interest_group', 'Interest Group')],
        default='company',
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        domain="[('is_company', '=', True)]",
    )
    interest_group_id = fields.Many2one(
        comodel_name="res.partner.interest.group",
        string="Interest Group",
    )
    begin_date = fields.Date(string="Begin Date", copy=False)
    end_date = fields.Date(string="End Date", copy=False)
    invoiced_amount = fields.Float(string="Invoiced amount", compute="_compute_invoice_ids")
    yer_amount = fields.Float(
        string="Year-end rebate amount",
        compute="_compute_yer_amount",
        store=True
    )
    stage_id_in_progress = fields.Many2one(
        comodel_name="sale.yer.stage",
        string="Stage in progress",
        compute="_compute_stage_id_in_progress",
        store=True
    )
    stage_ids = fields.One2many(
        comodel_name="sale.yer.stage",
        inverse_name='yer_id',
        string="Stage",
        copy=True
    )
    stage_ids_count = fields.Integer(string="Stages count", compute="_compute_stage_ids_count", store=True)
    discount_percentage = fields.Float(
        string="Discount percentage",
        compute="_compute_discount_percentage",
        store=True
    )
    amount_before_next_stage = fields.Float(
        string="Amount before next stage",
        compute="_compute_amount_before_next_stage",
        store=True
    )
    yer_amount_next_stage = fields.Float(
        string="Year-end rebate amount next stage",
        compute="_compute_yer_amount_next_stage"
    )
    user_id = fields.Many2one(string="Supervisor", comodel_name="res.users", compute="_compute_user_id", store=True)
    order_ids = fields.Many2many(
        comodel_name="sale.order",
        string="Orders",
        compute="_compute_order_ids",
    )
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Invoices",
        compute="_compute_invoice_ids",
    )
    order_count = fields.Integer(string='Orders Count', compute="_compute_order_ids")
    invoice_count = fields.Integer(string='Invoices Count', compute="_compute_invoice_ids")
    move_id = fields.Many2one(comodel_name='account.move', string='Credit note', readonly=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True)


    @api.depends('stage_id_in_progress', 'stage_id_in_progress.amount_before_reach_next_stage')
    def _compute_yer_amount_next_stage(self):
        for this in self:
            this.yer_amount_next_stage = (
                this.stage_id_in_progress.yer_stage_achieved if this.stage_id_in_progress else 0.0
            )

    @api.depends('stage_ids', 'stage_ids.amount_to_reach', 'stage_ids.name', 'stage_ids.discount',
                 'stage_ids.progression_stage')
    def _compute_discount_percentage(self):
        for this in self:
            stage = this.stage_ids.filtered(lambda s: s.progression_stage == 100)
            this.discount_percentage = stage.sorted('amount_to_reach')[-1].discount if stage else 0.0

    @api.depends('invoiced_amount', 'discount_percentage')
    def _compute_yer_amount(self):
        for this in self:
            this.yer_amount = this.invoiced_amount * this.discount_percentage

    @api.depends('domain', 'partner_id', 'begin_date', 'end_date', 'partner_id.sale_order_ids')
    def _compute_order_ids(self):
        for this in self:
            if not this.domain:
                this.order_ids = [(5,)]
                this.order_count = 0
                continue
            domain = [
                ('date_order', '>=', this.begin_date),
                ('date_order', '<=', this.end_date),
                ('id', 'not in', self.env['sale.yer'].move_id.ids),
                ('state', 'in', ['sale', 'done'])
            ]
            if this.domain == 'company':
                domain.append(('partner_id.id', 'child_of', this.partner_id.id))
            elif this.domain == 'interest_group':
                domain.append(('partner_id.id', 'child_of', this.interest_group_id.partner_id.ids))
            this.order_ids = this.env['sale.order'].search(domain)
            this.order_count = len(this.order_ids)

    @api.depends('domain', 'partner_id', 'begin_date', 'end_date', 'partner_id.invoice_ids',
                 'partner_id.invoice_ids.state')
    def _compute_invoice_ids(self):
        for this in self:
            if (not this.domain or (this.domain == 'company' and not this.partner_id) or
                    (this.domain == 'interest_group' and not this.interest_group_id.partner_id)):
                this.invoice_ids = [(5,)]
                this.invoice_count = 0
                this.invoiced_amount = 0
                continue
            domain = [('invoice_date', '>=', this.begin_date),
                    ('invoice_date', '<=', this.end_date),
                    ('state', '=', 'posted'),
                      ('is_yer', '!=', True)]
            if this.domain == 'company':
                domain.append(('partner_id.id', 'child_of', this.partner_id.id))
            elif this.domain == 'interest_group':
                domain.append(('partner_id.id', 'child_of', this.interest_group_id.partner_id.ids))
            this.invoice_ids = this.env['account.move'].search(domain)
            this.invoice_count = len(this.invoice_ids)
            this.invoiced_amount = sum(this.invoice_ids.mapped('amount_untaxed_signed'))

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
            return action

        ctx = self.env.context.copy()
        ctx['default_move_type'] = 'out_invoice'
        ctx['default_partner_id'] = self.partner_id.id
        action['context'] = ctx
        return action

    def action_view_order(self):
        self.ensure_one()
        orders = self.mapped('order_ids').ids
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }
        if len(orders) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': orders[0],
            })
        else:
            action.update({
                'name': _('Sources Sale Orders %s', self.name),
                'domain': [('id', 'in', orders)],
                'view_mode': 'tree,form',
            })
        return action

    @api.depends('stage_ids', 'stage_ids.amount_to_reach', 'stage_ids.name')
    def _compute_stage_id_in_progress(self):
        for this in self:
            stage = this.stage_ids.filtered(lambda stage: stage.progression_stage < 100)
            if stage:
                this.stage_id_in_progress = stage.sorted('amount_to_reach')[0]
            elif this.stage_ids:
                this.stage_id_in_progress = this.stage_ids.sorted('amount_to_reach')[-1]

    @api.depends('stage_id_in_progress', 'stage_id_in_progress.amount_before_reach_next_stage')
    def _compute_amount_before_next_stage(self):
        for this in self.filtered(lambda l: l.stage_id_in_progress):
            this.amount_before_next_stage = this.stage_id_in_progress.amount_before_reach_next_stage

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.now()
                )
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.yer', sequence_date=seq_date) or _("New")
            return super().create(vals_list)

    def action_draft(self):
        return self.write({
            'state': 'draft'
        })

    def action_confirm(self):
        res = self.write({
            'state': 'confirmed'
        })
        self._compute_state()
        return res

    def action_cancel(self):
        return self.write({
            'state': 'cancel'
        })

    @api.depends('end_date')
    def _compute_state(self):
        for this in self.filtered(lambda l: l.state == 'confirmed' and l.end_date < fields.Date.today()):
            this.state = 'done'

    @api.depends('partner_id')
    def _compute_user_id(self):
        for this in self:
            this.user_id = this.partner_id.user_id if this.partner_id else False

    @api.depends('stage_ids')
    def _compute_stage_ids_count(self):
        for this in self:
             this.stage_ids_count = len(this.stage_ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for this in self:
            if this.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "You can not delete a confirmed or a done Year-end rebate."))

    @api.constrains('domain', 'partner_id', 'interest_group_id', 'begin_date', 'end_date')
    def _check_partner_period_warning(self):
        """ Warn if partner or interest group already have a year-end rebate on this period"""
        domain = [
            '&', '|', '&',
            ('begin_date', '<=', self.begin_date),
            ('end_date', '>=', self.begin_date),
            '|', '&',
            ('begin_date', '<=', self.end_date),
            ('end_date', '>=', self.end_date),
            '|', '&',
            ('begin_date', '>=', self.begin_date),
            ('begin_date', '<=', self.end_date),
            '&',
            ('end_date', '>=', self.begin_date),
            ('end_date', '<=', self.end_date),
            '&',
            ('domain', '=', self.domain),
            '&',
            ('id', '!=', self.id),
        ]
        if self.domain == 'company':
            domain += [('partner_id.id', '=', self.partner_id.id)]
        elif self.domain == 'interest_group':
            domain += [('interest_group_id.id', '=', self.interest_group_id.id)]
        yer = self.env['sale.yer'].search(domain)
        if yer:
            raise UserError(_("A year-end rebate already exist for this partner/interest group on this period"))

    @api.constrains('begin_date', 'end_date')
    def check_partner_period_warning(self):
        """ Warn if partner or interest group already have a year-end rebate on this period"""
        if self.begin_date > self.end_date:
            raise UserError(_("Begin date need to be before end date"))

    def create_credit_note(self):
        """ Create credit note(s) for the given Year-end rebate(s).
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']
        product_variant = self.env.ref('s6r_year_end_rebate.product_sale_yer').product_variant_id
        line_vals = Command.create({
                'display_type': 'product',
                'name':  product_variant.name,
                'product_id': product_variant.id,
                'quantity': 1,
                'price_unit': self.yer_amount,
                'tax_ids': [],
                'sale_line_ids': [],
                'is_downpayment': True,
            })

        invoice_vals = {
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [line_vals],
            'is_yer': True,
        }
        self.move_id = self.env['account.move'].sudo().with_context(default_move_type='out_refund').create([invoice_vals])
        return self.move_id

