from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    is_yer = fields.Boolean(string='Is Year-end Rebate', default=False)
