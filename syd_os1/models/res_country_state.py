# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ResCountryState(models.Model):
    _inherit = 'res.country.state'
    
    os1_code = fields.Char('OS1 Code')