from odoo import fields, models, api, _, os
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    na_stone_color = fields.Many2one('na.stone.color', string='Colore Pietra')

class NaStoneColor(models.Model):
    _name = 'na.stone.color'

    color = fields.Char(string="Colore")

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, record.color))
        return res