# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dis_company_project_id = fields.Many2one(related='company_id.dis_project_id', readonly=False)
    dis_sftp = fields.Boolean(related='company_id.dis_sftp', readonly=False)
    dis_ftp_host = fields.Char(related='company_id.dis_ftp_host', readonly=False)
    dis_ftp_user = fields.Char(related='company_id.dis_ftp_user', readonly=False)
    dis_ftp_password = fields.Char(related='company_id.dis_ftp_password', readonly=False)
    dis_ftp_in_path = fields.Char(related='company_id.dis_ftp_in_path', readonly=False)
    dis_ftp_stl_path = fields.Char(related='company_id.dis_ftp_stl_path', readonly=False)
