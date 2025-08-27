# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    qapla_trans = fields.Char(string='Qapla Name')
    qapla_1 = fields.Boolean(string='Qapla 1?', copy=False)
