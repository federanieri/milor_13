# -*- coding: utf-8 -*-

from uuid import uuid1

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    odas2_company_url = fields.Char(related='company_id.odas2_url', readonly=False)
    odas2_company_test_url_regex = fields.Char(related='company_id.odas2_test_url_regex', readonly=False)
    odas2_company_access_token = fields.Char(related='company_id.odas2_access_token', readonly=False)
    odas2_company_stream_ids = fields.One2many(related='company_id.odas2_stream_ids', readonly=False)
    odas2_company_so_partner_id = fields.Many2one(related='company_id.odas2_so_partner_id', readonly=False)
    odas2_company_so_user_id = fields.Many2one(related='company_id.odas2_so_user_id', readonly=False)
    odas2_company_so_pricelist_id = fields.Many2one(related='company_id.odas2_so_pricelist_id', readonly=False)
    odas2_company_ps_mail_channel_id_when_orphan = fields.Many2one(related='company_id.odas2_ps_mail_channel_id_when_orphan', readonly=False)
    odas2_company_pp_force_commercehub_code = fields.Boolean(related='company_id.odas2_pp_force_commercehub_code', readonly=False)

    def action_generate_new_token(self):
        self.odas2_company_access_token = str(uuid1())
        return True
