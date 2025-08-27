# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
    package_carrier_type = fields.Selection(selection_add=[("gls_italy", "GLS Italy")])
