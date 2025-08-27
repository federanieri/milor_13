# -*- coding: utf-8 -*-
from odoo import api, fields, models, registry, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    need_txt_stl = fields.Boolean(default=False)
