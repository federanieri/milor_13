from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    bulk_validate = fields.Boolean(string='Abilita Validazione Massiva')

