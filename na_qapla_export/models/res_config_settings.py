from odoo import models, fields, api


class FTPOdooConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    qapla_ftp_host = fields.Char("Qapla FTP Host")
    qapla_ftp_user = fields.Char("Qapla FTP User")
    qapla_ftp_password = fields.Char("Qapla FTP Password")

    @api.model
    def get_values(self):
        res = super(FTPOdooConfiguration, self).get_values()
        ir_values = self.env['ir.config_parameter']

        qapla_ftp_host = ir_values.get_param('qapla_ftp_host')
        qapla_ftp_user = ir_values.get_param('qapla_ftp_user')
        qapla_ftp_password = ir_values.get_param('qapla_ftp_password')

        res.update({
            'qapla_ftp_host': qapla_ftp_host,
            'qapla_ftp_user': qapla_ftp_user,
            'qapla_ftp_password': qapla_ftp_password,
        })

        return res

    def set_values(self):
        super(FTPOdooConfiguration, self).set_values()

        ir_values = self.env['ir.config_parameter']
        ir_values.sudo().set_param('qapla_ftp_host', self.qapla_ftp_host)
        ir_values.sudo().set_param('qapla_ftp_user', self.qapla_ftp_user)
        ir_values.sudo().set_param('qapla_ftp_password', self.qapla_ftp_password)
        return True