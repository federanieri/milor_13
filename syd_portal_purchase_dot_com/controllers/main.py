# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os
import tempfile
import xlsxwriter
from collections import OrderedDict
from datetime import datetime, timedelta
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, content_disposition
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary
import logging
import io
from xlsxwriter.utility import xl_rowcol_to_cell
from odoo.addons.web.controllers.main import ReportController
try:
    from BytesIO import BytesIO
except ImportError:
    from io import BytesIO
import zipfile
#import urllib2

_logger = logging.getLogger(__name__)

def file_get_contents(filename, use_include_path=0, context=None, offset=-1, maxlen=-1):
    if (filename.find('://') > 0):
        ret = urllib2.urlopen(filename).read()
        if (offset > 0):
            ret = ret[offset:]
        if (maxlen > 0):
            ret = ret[:maxlen]
        return ret
    else:
        fp = open(filename, 'rb')
        try:
            if (offset > 0):
                fp.seek(offset)
            ret = fp.read(maxlen)
            return ret
        finally:
            fp.close()

class CustomerPortal(CustomerPortal):
    
    def take_in_charge(self,ids):
        orders = request.env['purchase.order'].browse(ids)
        orders.sudo().write({
                      'in_charge':True,
                      'spedito_da_fornitore':False,
                      'spedito_in_galvanica':False
                      })
    
    def spedito_fornitore(self,ids):
        orders = request.env['purchase.order'].browse(ids)
        orders.write({
                      'in_charge':False,
                      'spedito_da_fornitore':True,
                      'spedito_in_galvanica':False
                      })
       
    def spedito_galvanica(self,ids):
        orders = request.env['purchase.order'].browse(ids)
        orders.write({
                      'in_charge':False,
                      'spedito_da_fornitore':False,
                      'spedito_in_galvanica':True
                      })
    
    def print_po_pdf(self, ids):
            pdf, _ = request.env.ref('syd_portal_purchase_dot_com.action_report_purchase_production_order').sudo().render_qweb_pdf(ids)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)   

    def print_po_pdf_product(self, ids):
            pdf = False
            
            if not ids:
                return False
            pdf, _ = request.env.ref('syd_product_report.action_print_products_per_vendor').sudo().render_qweb_pdf(ids)
            
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            
            if 'take_attachment' in request.env.context:
                b64_pdf = base64.b64encode(pdf)
                attachment_id = request.env['ir.attachment'].sudo().create({
                            'name': '{}{}{}'.format('products_for_vendor',datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'),'.pdf'),
                            'type': 'binary',
                            'datas': b64_pdf,
                            'public': True,
                            'mimetype': 'application/x-pdf'
                        })
                return attachment_id
            
            request.env['purchase.order'].browse(ids).sudo().write({
                  'in_charge':True,
                  'spedito_da_fornitore':False,
                  'spedito_in_galvanica':False,
            })
            
            return request.make_response(pdf, headers=pdfhttpheaders)
        
    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, report_type=None, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        
        if report_type=='xls':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(v)
            generated_excel = self.generate_po_excel(order_list)
            return request.redirect(generated_excel.get('url'))
        
        if report_type=='txt':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            context = request.env.context.copy()
            context.update({'prefix': 'txt1'})
            request.env.context = context
            generated_txt = self.generate_txt_stl_file(order_list) 
            return generated_txt and request.redirect(generated_txt.get('url'))

        if report_type=='stl':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            context = request.env.context.copy()
            context.update({'prefix': 'stl'})
            request.env.context = context
            generated_txt = self.generate_txt_stl_file(order_list)
            return generated_txt
                
        if report_type=='pdf':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            return self.print_po_pdf(order_list)
        
        if report_type=='pdf_product':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            return self.print_po_pdf_product(order_list)
                
        if report_type=='action':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            self.take_in_charge(order_list)
            return request.redirect(request.httprequest.base_url)

        if report_type=='action_spedito':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            self.spedito_fornitore(order_list)            
            return request.redirect(request.httprequest.base_url)
        
        if report_type=='action_galvanica':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            self.spedito_galvanica(order_list)
            return request.redirect(request.httprequest.base_url)
        
        if report_type=='zip':
            order_list = []
            for k, v in kw.items():
                if k.startswith('po_'):
                    order_list.append(int(v))
            generated_zip = self.generate_zip_file(order_list)
            return generated_zip
                
        return super(CustomerPortal, self).portal_my_purchase_orders(page, date_begin, date_end, sortby, filterby, **kw)

    def download_document_zip(self, tab_id, bin_file=False):
        attachment_ids = request.env['ir.attachment'].sudo().search([('id', 'in', tab_id)])
        file_dict = {}
        for attachment_id in attachment_ids:
            file_store = attachment_id.store_fname
            if file_store:
                file_name = attachment_id.name
                file_path = attachment_id._full_path(file_store)
                file_dict["%s:%s" % (file_store, file_name)] = dict(path=file_path, name=file_name)
        zip_filename = datetime.now()
        zip_filename = "%s.zip" % zip_filename
        bitIO = BytesIO()
        zip_file = zipfile.ZipFile(bitIO, "w", zipfile.ZIP_DEFLATED)
        for file_info in file_dict.values():
            zip_file.write(file_info["path"], file_info["name"])
        if bin_file:
            zip_file.writestr(bin_file.get('filename'), base64.b64decode(bin_file.get('bin')))
        zip_file.close()
        return request.make_response(bitIO.getvalue(),
                                     headers=[('Content-Type', 'application/x-zip-compressed'),
                                              ('Content-Disposition', content_disposition(zip_filename))])

    def generate_zip_file(self, orders=False):
        purchases=False
        tab_id = []
        bin_file = {}
        
        context = request.env.context.copy()
        context.update({'take_attachment': True})
        request.env.context = context
        if orders:
            purchases = request.env['purchase.order'].browse(orders)
        else:
            return False
        
        purchases_ol_stl = purchases.order_line.filtered(lambda x: x.dis_task_id and x.dis_task_id.sudo().stl_file)
        purchases_ol_txt = purchases.order_line.filtered(lambda x: x.product_po_id.sudo().txt_type == 'txt1')
        tasks_txt = purchases_ol_txt.mapped('dis_task_id').sudo()

        attachment_stl_ids = self.return_stl_files(purchases_ol_stl, att=True)
        attachment_txt = tasks_txt.with_context({'into_zip':True,'filename':'TXT.txt' if len(tasks_txt) > 1 else False}).sudo().action_download_txt(only_orphans=False) if tasks_txt else False
        attachment_pdf = self.print_po_pdf_product(purchases.ids)
        # for adding pdf and txt's (list of attachments)
        if attachment_txt:
            tab_id.append(attachment_txt.id)
        if attachment_pdf:
            tab_id.append(attachment_pdf.id)
        if attachment_stl_ids:
            if isinstance(attachment_stl_ids, list):
                bin_file = {
                    'bin': attachment_stl_ids[0],
                    'filename': attachment_stl_ids[1]
                    }
            elif isinstance(attachment_stl_ids, int):
                tab_id.append(attachment_stl_ids)
        #Apply take_in_charge = True
        self.take_in_charge(orders or purchases.ids)
        for purchase in request.env['purchase.order'].browse(orders):
            purchase.sudo().write({
              'downloaded_stl':True if purchase.id in  purchases_ol_stl.order_id.ids else False,
              'downloaded_txt':True if purchase.id in purchases_ol_txt.order_id.ids else False,
              'in_charge':True if attachment_pdf else False
        })
        if tab_id:
            return self.download_document_zip(tab_id, bin_file)
        
            
    def generate_po_excel(self, orders):
        filename = '{}{}{}'.format('purchase_orders_',datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'),'.xlsx')
        path = os.path.join(tempfile.gettempdir(), filename)
        
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet('Proposal')
        worksheet = self._generate_po_excel(worksheet,orders,workbook)
        workbook.close()
        
        file = open(path,'rb')
        vals = {'name':filename,
                'type':'binary',
                'public':True,
                'datas':base64.b64encode(file.read())
                }
        attachment_id = request.env['ir.attachment'].sudo().create(vals)
        file.close()
        
        return {
            'type':'ir.actions.act_url',
            'url':'/web/content/%s?download=true' % attachment_id.id,
            'target':'self'
            }
        
    def generate_txt_stl_file(self, orders):
        purchases = False
        prefix = request.env.context.get('prefix')
        url = False
        if orders:
            purchases = request.env['purchase.order'].browse(orders)
        else:
            return False
        
        if prefix == 'stl':
            ol = purchases.order_line.filtered(lambda x: x.dis_task_id and x.dis_task_id.sudo().stl_file)
            url = self.return_stl_files(ol)
        elif prefix == 'txt1':
            purchases = purchases.filtered(lambda x: x.order_line.filtered(lambda x: x.product_po_id.sudo().txt_type == prefix))  
            url = self.return_txt_files(purchases)
        return url
    
    def return_stl_files(self, order_lines, att=False):
        if not order_lines:
            return False
        else:
            if not att:
                order_lines.order_id.sudo().write({'downloaded_stl':True})
            if len(order_lines) == 1:
                if not att:
                    url = {
                        'type':'ir.actions.act_url',
                        'url':'/web/content?model=purchase.order.line&id=%d&field=dis_task_stl_file&filename=%s.stl&download=true' % (order_lines.id, order_lines.order_id.name + '_' + str(order_lines.id)),
                        'target':'self'
                    }
                    return request.redirect(url.get('url'))
                return [order_lines.mapped('dis_task_stl_file')[0], order_lines.order_id.name + '_' + str(order_lines.id) + '.stl']
            else:
                return self.download_stl_zip(order_lines, att)
    
    def download_stl_zip(self, order_lines, att=False):
        zip_filename = 'STL_' + datetime.now().strftime('_%Y-%m-%d_%H-%M-%S')
        zip_attachment = self.create_zip_file(zip_filename, order_lines, att)
        return zip_attachment

    def create_zip_file(self, filename, order_lines, att=False):
        route = '/tmp/DOWNLOAD_ZIP/'
        if not os.path.exists(route):
            os.makedirs(route)
        if os.path.exists(route):
            ruta = os.path.join(route, filename)
            archivo_zip = ruta + '.zip'
        try: 
            with zipfile.ZipFile(archivo_zip, 'w') as fw_f:
                for ol in order_lines:
                    fw_f.writestr(ol.order_id.name + '_' + str(ol.id)+'.stl', base64.b64decode(ol.dis_task_stl_file),
                                     compress_type=zipfile.ZIP_DEFLATED)
            fw_f.close()
            obj_att = self.create_attachment(archivo_zip, filename+'.zip')
            if obj_att:
                if att:
                    return obj_att.id
                else:
                    url = {
                        'type':'ir.actions.act_url',
                        'url':'/web/content/%s?download=true' % obj_att.id,
                        'target':'self'
                        }
                    return request.redirect(url.get('url'))
            else:
                return False
        except Exception as ex:
            _logger.info("Error trying to open and write the document.")
        os.remove(archivo_zip)

    def create_attachment(self, archivo_zip, filename):
        contenido_zip = file_get_contents(archivo_zip)
        bin_data = base64.b64encode(contenido_zip)
        attachment = {
            'name': filename,
            'db_datas': bin_data,
            'datas': bin_data,
            'file_size': len(bin_data),
            'mimetype': 'application/x-zip-compressed',
        }
        obj_att = request.env['ir.attachment'].sudo().create(attachment)
        return obj_att

    def return_txt_files(self, purchases):
        # INFO: sorts by product_id to group same products code when rendering as a TXT.
        tasks = purchases.sudo().order_line.sorted(lambda x: x.product_id.id).mapped('dis_task_id')
        if not tasks:
            return False
        attachment_id = tasks.with_context({'into_zip':True,'filename':'TXT.txt' if len(tasks) > 1 else False}).sudo().action_download_txt(only_orphans=False)
        purchases.sudo().write({'downloaded_txt':True})                 
        return {
            'type':'ir.actions.act_url',
            'url':'/web/content/%s?download=true' % attachment_id.id,
            'target':'self'
            }
        
    def _generate_po_excel(self, worksheet=False, orders=False, workbook=False):
        field_labels = [
            "PO (Source)",
            "Immagine",
            "SKU",
            "Milor Code",
            "Plating",
            "Size",
            "Prezzo",
            "Quantità",
            "Weight (gr)",
            "Consegnata",
            "Da consegnare",
            "Barcode del PO"
        ]
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        worksheet.set_column(0, len(field_labels), 30)

        col = 0
        for label in field_labels:
            worksheet.write(0, col, label, bold)
            col += 1
            
        row = 1
        for po in orders:
            purchase_id = request.env['purchase.order'].sudo().browse(int(po))
            money_format = workbook.add_format({'num_format': purchase_id.currency_id.symbol + ' #,##0.00'})
            money_format.set_align('left')
            barcode = ReportController.report_barcode(self, type='Code128',value=purchase_id.name, width=200, height=60)

            for po_line in purchase_id.order_line.filtered(lambda x: not x.display_type):
                worksheet.set_row(row, 98)
                
                source_name = purchase_id.name
                pp_id = po_line.sudo().product_of_service_id if purchase_id.parent_po_id else po_line.product_id

                image = pp_id.image_128
                default_code = pp_id.default_code
                plating = pp_id.plating_id.name
                size = pp_id.product_template_attribute_value_ids.filtered(lambda x: "SIZE" in x.attribute_id.with_context(lang=u'en_US').name.upper())
                milor_code = pp_id.milor_code
                weight = pp_id.weight_gr
                
                worksheet.write(row, 0, '{}'.format(source_name))
                if bool(image):
                    buf_image=io.BytesIO(base64.b64decode(image))
                    worksheet.insert_image(xl_rowcol_to_cell(row, 1), "image.jpg", {'image_data': buf_image})
                worksheet.write(row, 2, '{}'.format(default_code))
                worksheet.write(row, 3, milor_code)
                worksheet.write(row, 4, plating)
                worksheet.write(row, 5, size and size.name or '')
                worksheet.write(row, 6, po_line.price_unit,money_format)
                worksheet.write(row, 7, '{}'.format(po_line.product_qty))
                worksheet.write(row, 8, '{}'.format(weight))
                worksheet.write(row, 9, '{}'.format(po_line.qty_received))
                worksheet.write(row, 10, '{}'.format(po_line.product_qty - po_line.qty_received or 0))
                worksheet.insert_image(xl_rowcol_to_cell(row, 10), "image.jpg", {'image_data': io.BytesIO(barcode.data)})

                row += 1
        return worksheet

    
    # @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    # def portal_my_purchase_order(self, order_id=None, access_token=None, **kw):
    #     try:
    #         order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
    #     except (AccessError, MissingError):
    #         return request.redirect('/my')
    #
    #     values = self._purchase_order_get_page_view_values(order_sudo, access_token, **kw)
    #     return request.render("purchase.portal_my_purchase_order", values)
    