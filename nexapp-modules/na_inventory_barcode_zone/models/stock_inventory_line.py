# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    zone = fields.Char(string='Plateau')

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        res = super()._get_move_values(qty, location_id, location_dest_id, out)
        vals = {
            'zone': self.zone,
        }
        res.update(vals)
        return res
