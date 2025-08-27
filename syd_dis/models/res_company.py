# -*- coding: utf-8 -*-
from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    dis_project_id = fields.Many2one('project.project', 'DIS Project ID')
    dis_sftp = fields.Boolean()
    dis_ftp_host = fields.Char()
    dis_ftp_user = fields.Char()
    dis_ftp_password = fields.Char()
    dis_ftp_in_path = fields.Char()
    dis_ftp_stl_path = fields.Char()
