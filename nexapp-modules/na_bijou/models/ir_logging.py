# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields


class IrLogging(models.Model):
    _inherit = 'ir.logging'

    bijou_id = fields.Many2one(
        comodel_name='bijou.account',
        string='Bijou Account',
        index=1, ondelete='set null')
