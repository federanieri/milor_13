from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    custom_value = fields.Char(string='Custom Value', related='move_id.custom_value')
