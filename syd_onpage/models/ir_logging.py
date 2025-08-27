# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IrLogging(models.Model):
    # Private Attributes
    _inherit = 'ir.logging'

    # ------------------
    # Field Declarations
    # ------------------

    onpage_account_id = fields.Many2one(
        comodel_name='onpage.account',
        string='OnPage Account',
        index=1, ondelete='set null')
