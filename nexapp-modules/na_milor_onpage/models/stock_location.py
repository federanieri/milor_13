from odoo import fields, models, api

class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_onpage = fields.Boolean(string='Export onpage')
    onpage_str = fields.Char(string="Onpage string")