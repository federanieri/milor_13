# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    conversion_product_category = fields.Many2one('product.category', string='Product Category for Conversion',
                                                  config_parameter='base.conversion_product_category')
