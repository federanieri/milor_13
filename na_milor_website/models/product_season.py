from odoo import api, fields, models


class Season(models.Model):
    _inherit = 'product.season'
    _description = 'Season'

    is_promo_website = fields.Boolean(string='Mostra nelle promo')