# Copyright 2023 Scalizer (<https://www.scalizer.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_yer = fields.Boolean(string='Is Year-end Rebate', default=False)
