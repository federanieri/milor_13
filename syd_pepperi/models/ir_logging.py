# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IrLogging(models.Model):
    _inherit = 'ir.logging'

    pepperi_account_id = fields.Many2one(
        comodel_name='pepperi.account',
        string='Pepperi Account',
        index=1, ondelete='set null')
