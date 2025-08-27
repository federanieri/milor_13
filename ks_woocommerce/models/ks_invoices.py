# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMoveExtended(models.Model):
    _inherit = 'account.move.line'

    ks_discount_amount_value = fields.Float(string='Discount Amount', digits=(16, 4))
