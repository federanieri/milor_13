# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_code_os1 = fields.Selection([
        ('milor_account_code', 'Codice Contabilità'),
        ('milor_account_code_id', 'Nuovo Codice Contabilità')],
        default='milor_account_code_id',
        related='company_id.account_code_os1',
        string='Account code OS1',
        readonly=False)
