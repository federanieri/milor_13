from odoo import fields, models

class Zone(models.Model):
    _name = 'na.zone'

    name = fields.Char(string="Nome")