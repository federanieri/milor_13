# -*- coding: utf-8 -*-
from odoo import api, fields, models, registry, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    txt_type = fields.Selection([
        ('txt1', 'TXT (pers. only)'),
        ('txt2', 'TXT (need STL)'),
    ], default=False)
