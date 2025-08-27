# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import tempfile
import logging
import os
import io
import re

_logger = logging.getLogger(__name__)

class ImportTXT(models.TransientModel):
    _name = 'import.txt'
    _inherit = ['mail.thread','mail.alias.mixin']
    _description = 'Import TXT'
    
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        
        model_id = self.env['ir.model'].search([('model','=',self._name)]).id
        alias = self.env['mail.alias'].sudo().search([('alias_model_id','=',model_id)])
        attachments = msg_dict.get('attachments')
        
        if attachments:
            for attachment in attachments:
                if attachment.fname.endswith('.txt'):
                    fname = attachment.fname
                    content = attachment.content
                    self.execute(fname, content)   
            return super(ImportTXT,self).create({'alias_id':alias.id})
           
    def execute(self, fname, content):
        try:
            purchase = False
            sale = False
            stop = False
            path_file = os.path.join(tempfile.gettempdir(), fname)
            f = open(path_file,'wb')
            f.write(content)
            f.close()
            
            with open(path_file) as f:
                lines = f.readlines()
                for line in lines:
                    for match in re.findall(r'(\d{15})', line):
                        purchase = self.env['purchase.order'].search([('commercehub_po','=',match),('company_id','=',1)], limit=1)
                        sale = self.env['sale.order'].search([('commercehub_po','=',match),('company_id','=',1)], limit=1)
                        if purchase or sale:
                            self.manage_cancel_order(match, purchase, sale)
                            break
                        else:
                            template_id = self.env.ref('syd_mail_files.email_template_cancel_order_no_exist').id
                            template = self.env['mail.template'].browse(template_id)
                            user = self.env['res.users'].search([('id','=',2)])
                            template.send_mail(user.id, force_send=True)
                            stop = True
                            break
                    if purchase or sale or stop:
                        break
                        
        except Exception as e:
            _logger.error("The txt file could not be read: %s", str(e), exc_info=True)
            
        os.remove(path_file)          
             
    def manage_cancel_order(self, match, purchase=False, sale=False):
        try:
            
            if purchase:
                if purchase.po_status == 'new' and not (purchase.in_charge and purchase.downloaded_stl and purchase.downloaded_txt and purchase.purchase_order_type in ('rework_one','rework_two')):
                    purchase.button_cancel()
                    purchase.cancel_request = True
                    if sale:
                        sale.action_cancel()
                    purchase_group = self.env['purchase.order'].search([('commercehub_po','=',match),('company_id','=',2)], limit=1)
                    sale_group = self.env['sale.order'].search([('commercehub_po','=',match),('company_id','=',2)], limit=1)
                    if purchase_group:
                        purchase_group.button_cancel()
                    if sale_group:
                        sale_group.action_cancel()
                    template_id = self.env.ref('syd_mail_files.email_template_order_cancelled').id
                    template = self.env['mail.template'].browse(template_id)
                    purchase.with_context(force_send=True).message_post_with_template(template_id=template.id)
                if purchase.po_status == 'in_charge' or (purchase.in_charge or purchase.downloaded_stl or purchase.downloaded_txt):
                    if purchase.received_status == 'to_receive':
                        purchase.cancel_request = True
                        template_id = self.env.ref('syd_custom.email_template_cancel_purchase_order').id
                        template = self.env['mail.template'].browse(template_id)
                        purchase.with_context(force_send=True).message_post_with_template(template_id=template.id)

                    if purchase.received_status == 'received':
                        purchase.cancel_request = True
                        purchase.cancel_request_processed = True
                        template_id = self.env.ref('syd_mail_files.email_template_cencellazione_per_ordine').id
                        template = self.env['mail.template'].browse(template_id)
                        template.send_mail(purchase.id, force_send=True)
            elif sale:
                if sale.delivery_status == 'to_deliver':
                    sale.cancel_request = True
                    template_id = self.env.ref('syd_custom.email_template_cancel_sale_order').id
                    template = self.env['mail.template'].browse(template_id)
                    template.send_mail(sale.id, force_send=True)
                    
                if sale.delivery_status == 'delivered':
                    sale.cancel_request = True
                    sale.cancel_request_processed = True
                    template_id = self.env.ref('syd_mail_files.email_template_cencellazione_per_ordine_so').id
                    template = self.env['mail.template'].browse(template_id)
                    template.send_mail(sale.id, force_send=True)
                
        except Exception as e:
            _logger.error("Couldn't cancel order as an error occured: %s", str(e), exc_info=True)
