# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
import datetime
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import base64
import logging
import os
import tempfile
import xlsxwriter
import io 
from xlsxwriter.utility import xl_rowcol_to_cell

_logger = logging.getLogger(__name__)


class Purchase(models.Model):
    _inherit = "purchase.order"
    
    reminder_sent = fields.Boolean(string="Reminder Sent?")
    
    def show_pdf_to_vendors(self):
        for purchases in [self.browse().concat(*g) for k, g in groupbyelem(self.search([('received_status', 'in', ('to_receive','partial')),('date_approve','!=',False),('state','=','purchase'),('reminder_sent','=',False),('commercehub_co','!=',False),('company_id','=',1)]), itemgetter('partner_id'))]:       
            try:
                vendor = purchases.partner_id
                
                if vendor and purchases:
                    template_id = self.env.ref('syd_product_report.email_template_send_products_vendor').id
                    template = self.env['mail.template'].browse(template_id)

                    purchases_order = purchases.sorted(key = lambda r: r.delay_days, reverse=True)
                    data_id = self.create_pdf_attachment(purchases_order,vendor)
                    
                    template.attachment_ids = [(6,0, [data_id.id])]
                    template.send_mail(vendor.id, force_send=True)
                    template.attachment_ids = [(3, data_id.id)]
                    
                    for purchase in purchases_order:
                        purchase.reminder_sent = True
                        
            except Exception as ex:
                _logger.info('While sending mail to vendor: %s',str(ex))
                pass

    def create_pdf_file(self):
        """
            Create Custom Excel Attachment to add into an email template.
            :data_ids Return a list of attachments that will be included in the mail
        """

        vendor = self.partner_id
        
        lines_dict = {}
        product_list = []
        for po_lines in [self.env['purchase.order.line'].concat(*g) for k, g in groupbyelem(self.order_line.filtered(lambda x: x.product_po_id), itemgetter('product_po_id'))]:
            vendor_seller_id = po_lines.product_po_id.seller_ids.filtered(lambda x: x.name == po_lines[0].order_id.partner_id)
            product = po_lines.product_po_id
            product_list.append({'product_id':product,
                                 'total_qty':sum(po_lines.mapped('product_uom_qty')),
                                 'purchases':list({line.order_id for line in po_lines}),
                                 'note_vendor':vendor_seller_id[0].note_vendor if vendor_seller_id else False,
                                 'size':product.size or product.product_template_attribute_value_ids.filtered(lambda x: "SIZE" in x.attribute_id.with_context(lang=u'en_US').name.upper()).name})
        lines_dict['product'] = product_list
        return lines_dict

    def create_pdf_attachment(self,purchases=False,vendor=False):
        pdf, _ = self.env.ref('syd_product_report.action_print_products_per_vendor').sudo().render_qweb_pdf(purchases.ids)
        b64_pdf = base64.b64encode(pdf) 
        attachment_id = self.env['ir.attachment'].create({
                        'name': '{}{}{}'.format('products_for_vendor',datetime.datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'),'.pdf'),
                        'type': 'binary',
                        'datas': b64_pdf,
                        'public': True,
                        'mimetype': 'application/x-pdf'
                    })
        return attachment_id
    
    def action_daily_purchase_report(self):
        attachment_id = self.create_xls_file(datetime.date.today())

        if attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': "/web/content/?model=ir.attachment&id=" + str(
                    attachment_id.id) + "&filename_field=name&field=datas&download=true&name=" + attachment_id.name,
                'target': 'self'
            }

    def daily_purchase_report(self):
        try:
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            today_po = self.search([
                    ('create_date', '<=', yesterday.strftime("%Y-%m-%d 23:59:59")),
                    ('create_date', '>=', yesterday.strftime("%Y-%m-%d 00:00:00")),
                    ('state', '=', 'purchase'), ('commercehub_po', '!=', False), ('company_id', '=', 1)
                ])
            if today_po:
                xls_attachment = today_po.create_xls_file(yesterday)
                template_id = self.env.ref('syd_product_report.email_template_send_purchase_report').id
                template = self.env['mail.template'].browse(template_id)
                template.attachment_ids = [(6,0, [xls_attachment.id])]
                milor_user = self.env['res.users'].browse(2)
                template.send_mail(milor_user.partner_id.id, force_send=True)
                template.attachment_ids = [(3, xls_attachment.id)]
        except Exception as ex:
            _logger.info('While sending mail to vendor: %s',str(ex))

    def create_xls_file(self, yesterday=False):
        """
            Create Custom Excel Attachment to add into an email template.
        """
        filename = '{}{}{}'.format('purchase_orders', yesterday.strftime('_%Y-%m-%d'), '.xlsx')
        path = os.path.join(tempfile.gettempdir(), filename)
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet('Purchases')
        worksheet = self._generate_xls_daily_report(worksheet, workbook)
        workbook.close()
        
        file = open(path, 'rb')
        vals = {'name': filename,
                'type': 'binary',
                'public': True,
                'datas': base64.b64encode(file.read())
                }
        attachment_id = self.env['ir.attachment'].sudo().create(vals)
        file.close()
        return attachment_id
    
    def _generate_xls_daily_report(self, worksheet=False, workbook=False):
        field_labels = [
            "Image",
            "Vendor",
            "J#",
            "Brand",
            "Description",
            "Totale pezzi ordinati",
            "Totale pezzi x Vendor",
        ]
        
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        info = self.group_by_template()
        products_sorted = sorted(info, key=lambda x: (x['vendor'].name, x['uom_qty']), reverse=True)
        
        worksheet.set_column(0, len(field_labels), 30)

        col = 0
        for label in field_labels:
            worksheet.write(0, col, label, bold)
            col += 1

        row = 1
        tot_qty_per_vendor, tot_qty = 0, 0
        old_vendor = products_sorted and products_sorted[0]['vendor'].name

        for product in products_sorted:
            worksheet.set_row(row, 98)

            product_id = product['product']

            if product_id.image_128:
                buf_image=io.BytesIO(base64.b64decode(product_id.image_128))
                worksheet.insert_image(xl_rowcol_to_cell(row, 0), "image.jpg", {'image_data': buf_image})

            vendor = product['vendor'].name
            qty = product['uom_qty']
            worksheet.write(row, 1, '{}'.format(vendor))
            worksheet.write(row, 2, '{}'.format(product_id.qvc_code))
            worksheet.write(row, 3, '{}'.format(product_id.product_brand_id.name))
            worksheet.write(row, 4, '{} - {}'.format(product_id.product_brand_id.name,product_id.name))
            worksheet.write(row, 5, '{}'.format(qty))
            if old_vendor != vendor:
                worksheet.write(row - 1, 6, '{}'.format(tot_qty_per_vendor))
                old_vendor = vendor
                tot_qty_per_vendor = 0

            tot_qty_per_vendor += qty
            tot_qty += qty

            row += 1

        worksheet.write(row - 1, 6, '{}'.format(tot_qty_per_vendor))
        worksheet.write(row + 1, 4, 'Totale pezzi', bold)
        worksheet.write(row + 1, 5, '{}'.format(tot_qty), bold)

        return worksheet

    def group_by_template(self):
        info = []
        for k, g in groupbyelem(self.order_line.filtered(lambda x: x.product_po_id), key=lambda x: x.product_po_id.product_tmpl_id):
            info.append({'product': k,
                         'vendor': k.seller_ids[0].name if k.seller_ids else False,
                         'uom_qty': sum(v.product_uom_qty for v in g),
                         'uom': k.uom_id.name,
                         'in_stock': (not bool(self.env.ref('stock.route_warehouse0_mto').id in k.route_ids.ids)),
                         'sales': g})
        return info


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def daily_sale_report(self, cron_type=False):
        try:
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            today_sales = self.sudo().search([
                ('create_date', '<=', yesterday.strftime("%Y-%m-%d 23:59:59")),
                ('create_date', '>=', yesterday.strftime("%Y-%m-%d 00:00:00")),
                ('commercehub_po', '!=', False),
                ('company_id', '=', 2),
                ('as2_state', '=', 'error')
            ])
            if today_sales:
                xls_attachment = False
                template_id = False
                if not cron_type:
                    xls_attachment = today_sales.create_xls_sales_file(yesterday, cron_type)
                    if xls_attachment:
                        template_id = self.env.ref('syd_product_report.email_template_send_sale_report').id

                elif cron_type == 'missing':
                    # INFO: looks for just 'missing' not 'duplicated'.
                    sales = today_sales.filtered(lambda x: 'Missing custom_value' in x.as2_state_reason and 'Duplicated' not in x.as2_state_reason)
                    if sales:
                        xls_attachment = sales.create_xls_sales_file(yesterday, cron_type)
                        if xls_attachment:
                            template_id = self.env.ref('syd_product_report.email_template_send_sale_report_missing').id

                elif cron_type == 'duplicate':
                    # INFO: looks for 'duplicated' (maybe includes 'missing').
                    sales = today_sales.filtered(lambda x: 'Duplicated' in x.as2_state_reason)
                    if sales:
                        xls_attachment = sales.create_xls_sales_file(yesterday, cron_type)
                        if xls_attachment:
                            template_id = self.env.ref('syd_product_report.email_template_send_sale_report_duplicate').id

                template_id = template_id and self.env['mail.template'].browse(template_id)
                if template_id:
                    template_id.attachment_ids = [(6, 0, [xls_attachment.id])]
                    milor_user = self.env['res.users'].browse(2)
                    template_id.send_mail(milor_user.partner_id.id, force_send=True)
                    template_id.attachment_ids = [(3, xls_attachment.id)]
        except Exception as ex:
            _logger.info('While sending mail to vendor: %s',str(ex))

    def create_xls_sales_file(self, yesterday=False, cron_type=False):
        if not cron_type:
            filename = '{}{}{}'.format('sales_order_failed', yesterday.strftime('_%Y-%m-%d'), '.xlsx')
        else:
            filename = '{}{}{}{}'.format('sales_order_failed_', cron_type, yesterday.strftime('_%Y-%m-%d'), '.xlsx')

        path = os.path.join(tempfile.gettempdir(), filename)
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet('Sale Orders')
        if not cron_type:
            self._generate_xls_daily_report_sales(worksheet, workbook)
        elif cron_type == 'missing':
            self._generate_xls_daily_report_sales_missing(worksheet, workbook)
        elif cron_type == 'duplicate':
            self._generate_xls_daily_report_sales_duplicate(worksheet, workbook)
        workbook.close()
        
        file = open(path,'rb')
        vals = {
            'name':filename,
            'type':'binary',
            'public':True,
            'datas':base64.b64encode(file.read())
        }
        attachment_id = self.env['ir.attachment'].sudo().create(vals)
        file.close()
        return attachment_id
    
    def _generate_xls_daily_report_sales(self, worksheet=False, workbook=False):
        field_labels = [
            "CommerceHub CO",
            "CommerceHub PO",
            "Tipo di Errore"
        ]
        
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        worksheet.set_column(0, len(field_labels), 30)

        col = 0
        for label in field_labels:
            worksheet.write(0, col, label, bold)
            col += 1

        row = 1
        for rec in self:
            worksheet.write(row, 0, '{}'.format(rec.commercehub_co))
            worksheet.write(row, 1, '{}'.format(rec.commercehub_po))
            worksheet.write(row, 2, '{}'.format(rec.as2_state_reason if rec.as2_state_reason else ''))

            row += 1
        return worksheet

    def _generate_xls_daily_report_sales_duplicate(self, worksheet=False, workbook=False):
        field_labels = [
            "PO#",
            "CO#",
            "Vendor SKU",
            "Merchant SKU",
            "Delivery Status"
        ]
        
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        worksheet.set_column(0, len(field_labels), 30)

        col = 0
        for label in field_labels:
            worksheet.write(0, col, label, bold)
            col += 1

        row = 1
        for rec in self:
            sale_order_id = self.env['sale.order'].search(
                [('commercehub_co', '=', rec.commercehub_co), ('commercehub_po', '!=', False), ('company_id', '=', 2),
                 ('as2_state', 'not in', ['error'])])
            for line in rec.order_line.filtered(lambda x: x.product_id):
                worksheet.write(row, 0, '{}'.format(line.order_id.commercehub_po))
                worksheet.write(row, 1, '{}'.format(line.order_id.commercehub_co))
                worksheet.write(row, 2, '{}'.format(line.product_id.qvc_complete_code))
                worksheet.write(row, 3, '{}'.format(line.product_id.commercehub_code))
                worksheet.write(row, 4, '{}'.format(
                    sale_order_id.delivery_status and dict(self._fields['delivery_status'].selection).get(
                        sale_order_id.delivery_status) or ""))
                row += 1

        return worksheet
    
    def _generate_xls_daily_report_sales_missing(self, worksheet=False, workbook=False):
        field_labels = [
            "PO#",
            "CO#",
            "Vendor SKU",
            "Merchant SKU"
        ]
        
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        worksheet.set_column(0, len(field_labels), 30)

        col = 0
        for label in field_labels:
            worksheet.write(0, col, label, bold)
            col += 1

        row = 1
        for rec in self:
            for line in rec.order_line.filtered(lambda x: x.product_id):
                worksheet.write(row, 0, '{}'.format(line.order_id.commercehub_po))
                worksheet.write(row, 1, '{}'.format(line.order_id.commercehub_co))
                worksheet.write(row, 2, '{}'.format(line.product_id.qvc_complete_code))
                worksheet.write(row, 3, '{}'.format(line.product_id.commercehub_code))
            row += 1

        return worksheet
