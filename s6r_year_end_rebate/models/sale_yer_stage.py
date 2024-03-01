# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging
from datetime import date

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleYerStage(models.Model):
    _name = 'sale.yer.stage'
    _inherit = 'analytic.mixin'
    _description = "Year-end rebate stage"
    _rec_names_search = ['name', 'yer_id.name']
    _order = 'yer_id, amount_to_reach, id'

    name = fields.Char(string='Name', compute="compute_name")
    amount_to_reach = fields.Float(string='Amount to reach', required=True)
    discount = fields.Float(string='Discount', required=True)
    progression_stage = fields.Float(string="Stage's progression", compute="_compute_progression_stage", store=True)
    amount_before_reach_next_stage = fields.Float(
        string='Amount before reach next stage',
        compute='_compute_amount_before_reach_next_stage'
    )
    yer_stage_achieved = fields.Float(string='YER stage achieved', compute='_compute_yer_stage_achieved', store=True)
    yer_id = fields.Many2one(
        comodel_name="sale.yer",
        string="YER Reference",
        required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one(string='Currency', related='yer_id.currency_id')

    @api.depends('discount', 'amount_to_reach')
    def _compute_yer_stage_achieved(self):
        for this in self:
            this.yer_stage_achieved = this.discount * this.amount_to_reach

    @api.depends('amount_to_reach', 'yer_id.invoiced_amount')
    def _compute_amount_before_reach_next_stage(self):
        for this in self:
            amount = this.amount_to_reach - this.yer_id.invoiced_amount
            this.amount_before_reach_next_stage = amount if amount > 0.0 else 0.0

    @api.depends('amount_to_reach', 'amount_before_reach_next_stage')
    def _compute_progression_stage(self):
        for this in self:
            this.progression_stage = ((this.amount_to_reach - this.amount_before_reach_next_stage) /
                                      this.amount_to_reach) * 100.0 if this.amount_to_reach else 100.0

    @api.depends('amount_to_reach', 'yer_id.stage_ids')
    def compute_name(self):
        for this in self:
            for i, stage in enumerate(this.yer_id.stage_ids.sorted('amount_to_reach')):
                stage.name = str(i+1)
