# -*- coding: utf-8 -*-
# Copyright (C) 2023 - Scalizer (<https://www.scalizer.fr>).
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Scalizer Year-end rebate',
    'version': '16.0.0.0.4',
    'author': 'Scalizer',
    'website': 'https://www.scalizer.fr',
    'summary': "Scalizer Year-end rebate",
    'sequence': 0,
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'account',
        'partner_interest_group',
        'product'
    ],
    'category': 'Generic Modules/Scalizer',
    'complexity': 'easy',
    'data': [
        "security/ir.model.access.csv",
        # Data
        "data/ir_sequence.xml",
        "data/product.xml",
        # Views
        "views/sale_yer_views.xml",
        "views/res_partner_views.xml",

        # Report

    ],
    'auto_install': False,
    'installable': True,
    'application': False,
}
