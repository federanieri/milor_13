# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class UtmSource(models.Model):
    _inherit = 'utm.source'

    operation_type = fields.Selection([('bb', 'B2B'), ('bc', 'B2C')], string='Tipo Operazione')
