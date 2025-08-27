# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class PartnerCategory(models.Model):
    _inherit = 'res.partner.category'
    
    os1_code = fields.Char('OS1 Code')