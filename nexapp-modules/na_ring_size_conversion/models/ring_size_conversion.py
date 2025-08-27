# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _


class RingSizeConversion(models.Model):
    _name = "ring.size.conversion"

    name = fields.Char(default='Size Conversion', string='Description')
    italian_size = fields.Float(string='Italian Size')
    french_size = fields.Float(string='French Size')
