# -*- coding: utf-8 -*-
import base64
import io
import os

from ftplib import FTP
import pysftp

from odoo import api, fields, models, registry, _

import logging

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    txt = fields.Char()
    stl_file = fields.Binary(attachment=True)
    dis_name = fields.Char(string="Nome Dis")
    txt_uploaded = fields.Boolean(default=False)
    stl_file_downloaded = fields.Boolean(default=False)
    last_ftp_error = fields.Char()

    order_line_id = fields.One2many('purchase.order.line', 'dis_task_id')
    product_id = fields.Many2one(related='order_line_id.product_id')
    txt_type = fields.Selection(related='order_line_id.product_id.txt_type')
    order_id = fields.Many2one(related='order_line_id.order_id')

    def action_download_txt(self, only_orphans=True):
        f = io.StringIO()

        names = []
        for rec in self:
            names += [rec.name]
            if rec.txt:
                if (only_orphans and not rec.stl_file) or not only_orphans:
                    f.write(rec.txt + '\n')

        if f.tell():
            f.seek(0)
            
            name = '_'.join(set(names)) + '.txt'

            if 'filename' in self._context and self._context.get('filename'):
                name = self._context.get('filename')                
            
            attachment = self.env['ir.attachment'].create({
                'datas': base64.b64encode(f.read().encode()),
                'name': name,
                'mimetype': 'application/txt',
            })
            f.close()

            if 'into_zip' in self._context:
                return attachment
        
            # INFO: fires downloading action request.
            return {
                'type': 'ir.actions.act_url',
                'url': "/web/content/?model=ir.attachment&id=" + str(attachment.id) + "&filename_field=name&field=datas&download=true&name=" + attachment.name,
                'target': 'self'
            }

        return False

    def _upload_txt(self, company=False, force_upload=False):
        company = company or self.env.company
        ftp_host = company.dis_ftp_host
        if ftp_host:
            remote_path = company.dis_ftp_in_path
            _logger.info("Uploading file object -> %s" % remote_path)

            sftp = company.dis_sftp
            ftp_user = company.dis_ftp_user
            ftp_password = company.dis_ftp_password

            if sftp:
                # INFO: sftp connection.
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None
                sftp = pysftp.Connection(ftp_host, username=ftp_user, password=ftp_password, port=22, cnopts=cnopts)
                sftp.cwd(remote_path)

                for rec in self:
                    if rec.txt_type == 'txt2' and rec.txt and (not rec.txt_uploaded or force_upload):
                        fo = io.StringIO(rec.txt + '\n')
                        filename = '%s.txt' % rec.name
                        try:
                            sftp.putfo(fo, filename)
                            rec.txt_uploaded = True
                        except Exception as E:
                            rec.last_ftp_error = str(E)
                        fo.close()

                sftp.close()
            else:
                # INFO: ftp not enabled.
                ftp = FTP(ftp_host, user=ftp_user, passwd=ftp_password)
                ftp.quit()
        return True

    def action_upload_txt(self):
        return self._upload_txt(force_upload=True)

    @api.model
    def _cron_upload_txt(self):
        for company in self.sudo().env['res.company'].search([]):
            ftp_host = company.dis_ftp_host
            if ftp_host:
                return self.search([('txt_type', '=', 'txt2'), ('txt', '!=', False), ('txt_uploaded', '=', False)])._upload_txt(company)
        return False

    @api.model
    def _cron_download_stl(self):
        for company in self.sudo().env['res.company'].search([]):
            ftp_host = company.dis_ftp_host
            if ftp_host:
                remote_path = company.dis_ftp_stl_path
                _logger.info("Downloading from %s" % remote_path)

                sftp = company.dis_sftp
                ftp_user = company.dis_ftp_user
                ftp_password = company.dis_ftp_password

                if sftp:
                    # INFO: sftp connection.
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None
                    sftp = pysftp.Connection(ftp_host, username=ftp_user, password=ftp_password, port=22, cnopts=cnopts)
                    sftp.cwd(remote_path)

                    for file in sftp.listdir():
                        _logger.info(file)
                        fo = io.BytesIO()
                        sftp.getfo(file, fo)

                        name = os.path.splitext(file)[0]
                        task = self.sudo().search([('name', '=', name)])
                        if task:
                            fo.seek(0)
                            task.write({
                                'stl_file': base64.encodebytes(fo.read()),
                                'stl_file_downloaded': True,
                                'last_ftp_error': ''
                            })
                            sftp.remove(file)
                            _logger.info('Task found: %s' % name)
                        else:
                            _logger.error('Task not found: %s' % name)
                        fo.close()
                    sftp.close()
                else:
                    # INFO: ftp not enabled.
                    ftp = FTP(ftp_host, user=ftp_user, passwd=ftp_password)
                    ftp.quit()
