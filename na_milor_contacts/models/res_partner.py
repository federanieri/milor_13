from odoo import fields, models

class Partner(models.Model):
    _inherit = 'res.partner'

    na_zone = fields.Many2many('na.zone', string='Zona')