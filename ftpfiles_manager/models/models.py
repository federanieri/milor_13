# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from ftplib import FTP
from odoo.exceptions import Warning
import io
import os 
import tempfile
import base64
import pysftp
import logging

_logger = logging.getLogger(__name__)

class FTPfilesManager(models.Model):
    _name = 'ftp.files.manager'
    _description = 'Configuration for FTP'

    def _download_fromFTP(self,folder1=False,folder2=False,folder3=False):   
        _logger.info("%s %s %s"%(folder1,folder2,folder3))     
        # un po di dati del server ftp           
        ftp_host = self.env['ir.config_parameter'].sudo().get_param('ftp_host')
        ftp_user = self.env['ir.config_parameter'].sudo().get_param('ftp_user')
        ftp_pass = self.env['ir.config_parameter'].sudo().get_param('ftp_password')
        sftp_config = self.env['ir.config_parameter'].sudo().get_param('sftp_config')
        sftp=False
        ftp=False
        
        # apro la conn
        if sftp_config:
            
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None            
            sftp = pysftp.Connection(ftp_host, username=ftp_user, password=ftp_pass, port=22, cnopts=cnopts)
            
            
            
            if folder1!= False and sftp.isdir(folder1):
                sftp.cwd(folder1)
            if folder2!= False and sftp.isdir(folder2):
                sftp.cwd(folder2)
            if folder3!= False and sftp.isdir(folder3):
                sftp.cwd(folder3)
                    
#             directory_structure = sftp.listdir_attr()   
            _logger.info(sftp.listdir())         
            for file in sftp.listdir():   
                _logger.info(file)            
                filepath = os.path.join(tempfile.gettempdir(), file)

                sftp.get(file, filepath)
                self.load_attachment(file, filepath, sftp_config, sftp)
            
        else:
            
            ftp = FTP(ftp_host, user=ftp_user, passwd=ftp_pass)
            
            if folder1!= False and sftp.isdir(folder1):
                ftp.cwd(folder1)
            if folder2!= False and sftp.isdir(folder2):
                ftp.cwd(folder2)
            if folder3!= False and sftp.isdir(folder3):
                ftp.cwd(folder3)
                
            for file in ftp.nlst():  
                filepath = os.path.join(tempfile.gettempdir(), file)
            
                with open(filepath, 'wb') as f:
                    ftp.retrbinary("RETR {}".format(file), f.write)
                self.load_attachment(file, filepath, sftp_config, ftp)
                                                
        if sftp:
            sftp.close()
        elif ftp:        
            ftp.quit()
    
    def load_attachment(self, file, filepath, sftp_config, conn):
        
        ftp_model_id = self.env['ir.config_parameter'].sudo().get_param('ftp_model_id')
        field_from_model = self.env['ir.config_parameter'].sudo().get_param('field_from_model')
        field_from_model_to_change_id = self.env['ir.config_parameter'].sudo().get_param('field_from_model_to_change_id')
        
        with open(filepath, 'rb') as fileRead:
            datas = fileRead.read()
    
        if len(file.split('.pdf')) > 1:
            _logger.info(file.split('.pdf'))     
            model_name = self.env['ir.model'].search([('id','=',int(ftp_model_id))])
            field_name = self.env['ir.model.fields'].search([('id','=',int(field_from_model))])
            
            field_id = self.env[model_name.model].search([(field_name.name,'=',file.split('.pdf')[0])])
            field_to_change_name = False
            if field_from_model_to_change_id :
                field_to_change_name = self.env['ir.model.fields'].search([('id','=',int(field_from_model_to_change_id))])
            try:
                if bool(field_id):
                    _logger.info('loading attachment')   
                    attachment_id = self.env['ir.attachment'].search([('res_id','=',field_id.id),('res_model','=',model_name.model),('name','=',file)])
                    
                    if bool(attachment_id):
                        attachment_id.unlink()
                    if field_to_change_name:
                        field_id.write({
                                     field_to_change_name.name : True   
                                        })
                    attachment_id.create({
                            'name': file,
                            'res_id': field_id.id,
                            'res_model': model_name.model,
                            'res_name': field_id.name,
                            'datas': base64.b64encode(datas) 
                        })
                
                    os.remove(filepath)
                    
                    if sftp_config:
                        conn.remove(file)
                    else:
                        conn.delete(file)

            except Exception as e:
                _logger.warning("The file couldn't be load. Error: %s" % e)
            
class FTPOdooConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    
    ftp_host = fields.Char("FTP Host")
    ftp_user = fields.Char("FTP User")
    ftp_password = fields.Char("FTP Password")
    ftp_model_id = fields.Many2one('ir.model',"Model Name")
    field_from_model = fields.Many2one('ir.model.fields',"Model's Field")
    sftp_config = fields.Boolean("Configure as SFTP Server")
    field_from_model_to_change_id = fields.Many2one('ir.model.fields',"Model's Field To Change")

    
    @api.model
    def get_values(self):
        res = super(FTPOdooConfiguration, self).get_values()
        ir_values = self.env['ir.config_parameter']
        
        ftp_host = ir_values.get_param('ftp_host')
        ftp_user = ir_values.get_param('ftp_user')
        ftp_password = ir_values.get_param('ftp_password')
        ftp_model_id = int(ir_values.get_param('ftp_model_id'))
        field_from_model = int(ir_values.get_param('field_from_model'))
        field_from_model_to_change_id = int(ir_values.get_param('field_from_model_to_change_id'))
        sftp_config = ir_values.get_param('sftp_config')
        
        res.update({
            'ftp_host':ftp_host,
            'ftp_user':ftp_user,
            'ftp_password':ftp_password,
            'ftp_model_id':ftp_model_id,
            'field_from_model':field_from_model,
            'sftp_config':sftp_config,
            'field_from_model_to_change_id':field_from_model_to_change_id
        })
        
        return res
    
    def set_values(self):
        super(FTPOdooConfiguration, self).set_values()
        
        ir_values = self.env['ir.config_parameter']
        ir_values.sudo().set_param('ftp_host', self.ftp_host)
        ir_values.sudo().set_param('ftp_user', self.ftp_user)
        ir_values.sudo().set_param('ftp_password', self.ftp_password)
        ir_values.sudo().set_param('ftp_model_id', int(self.ftp_model_id))
        ir_values.sudo().set_param('field_from_model', int(self.field_from_model))
        ir_values.sudo().set_param('sftp_config', self.sftp_config)
        ir_values.sudo().set_param('field_from_model_to_change_id', int(self.field_from_model_to_change_id))
        return True
        
