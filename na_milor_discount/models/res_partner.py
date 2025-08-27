from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    discount_line = fields.One2many('na.discount', 'partner_id', string='Sconti accordati')
