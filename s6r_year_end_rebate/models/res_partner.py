from odoo import fields, models, _

class ResPartner(models.Model):
    _inherit = "res.partner"

    yer_count = fields.Integer(string="YER count", compute="_compute_yer_count")
    yer_amount_in_progress = fields.Integer(string="YER amount N", compute="_compute_yer_amount_in_progress")

    def _compute_yer_count(self):
        for this in self:
            this.yer_count = this.env['sale.yer'].search_count([
                '|',
                ('partner_id.id', '=', this.id),
                ('interest_group_id.id', 'in', this.interest_group_ids.ids)
            ])

    def action_view_yer(self):
        self.ensure_one()
        yer = self.env['sale.yer'].search([
            '|',
            ('partner_id.id', '=', self.id),
            ('interest_group_id.id', 'in', self.interest_group_ids.ids)
        ]).ids
        action = {
            'res_model': 'sale.yer',
            'type': 'ir.actions.act_window',
        }
        if len(yer) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': yer[0],
            })
        else:
            action.update({
                'name': _('Sources Sale YER %s', self.name),
                'domain': [('id', 'in', yer)],
                'view_mode': 'tree,form',
            })
        return action

    def _compute_yer_amount_in_progress(self):
        for this in self:
            yer = this.env['sale.yer'].search([
                ('partner_id.id', '=', this.id),
                ('begin_date', '<=', fields.Date.today()),
                ('end_date', '>=', fields.Date.today())
            ])
            if len(yer) == 1:
                this.yer_amount_in_progress = yer.yer_amount
            else:
                this.yer_amount_in_progress = 0.0

