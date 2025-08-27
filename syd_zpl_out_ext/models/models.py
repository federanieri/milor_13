# -*- coding: utf-8 -*-
# © 2020 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
import json


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    zpl_out_ext = fields.Char('ZPL Default Output Ext', default="zpl")

    # INFO: acquires zpl ext from current user and zpl out exts from system config parameter.
    @api.model
    def get_zpl_out_exts(self):
        exts = self.env['ir.config_parameter'].sudo().get_param('zpl_out_exts')
        return {
            "selected_ext": self.env.user.zpl_out_ext,
            "exts":  exts and json.loads(exts) or None
        }

    # INFO: sets selected zpl out ext into user data.
    @api.model
    def set_zpl_out_ext(self, ext):
        self.env.user.sudo().write({
            'zpl_out_ext': ext
        })
