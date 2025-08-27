# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    zone = fields.Char(string='Plateau')


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    zone = fields.Char(string='Plateau', related="move_id.zone")

