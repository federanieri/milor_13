from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    free_use_qty = fields.Float(string='Free to use Qty', related='product_id.free_qty')
