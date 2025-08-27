from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.country'

    country_iso_code = fields.Char(string="Country ISO Code")
