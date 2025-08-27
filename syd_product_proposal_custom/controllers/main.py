# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.syd_product_proposal.controllers.main import CustomerPortal
import re, tempfile, datetime, os, xlsxwriter, base64,io
import logging

from xlsxwriter.utility import xl_rowcol_to_cell
_logger = logging.getLogger(__name__)
class CustomerPortal(CustomerPortal):
    
    
        
    def _generate_mts(self, worksheet=False, order_sudo=False,workbook=False):
        
        worksheet.set_column(0, 1, 18)
        
        
        worksheet.write(0, 0, 'Picture')
        worksheet.write(0, 1, 'Milor Reference')
        worksheet.write(0, 2, 'Title')
        worksheet.write(0, 3, 'Type')
        worksheet.write(0, 4, 'Description')
        worksheet.write(0, 5, 'Weight')
        worksheet.write(0, 6, 'Details')
        worksheet.write(0, 7, 'Color')
        
        worksheet.write(0, 8, 'Barcode')
        worksheet.write(0, 9, 'In stock')
        worksheet.write(0, 10, 'Internal Reference')
        worksheet.write(0, 11, 'Retail Price')
        
        worksheet.write(0, 12, 'Quantity proposed')
        worksheet.write(0, 13, 'Price')
        worksheet.write(0, 14, 'Quantity Accepted')
        
        worksheet.write(0, 15, 'Price Total Accepted')
        worksheet.write(0, 16, 'Comments or changes')

        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.write(0, 17, 'Customer Product Code')
        
        money_format = workbook.add_format({'num_format': order_sudo.currency_id.symbol + ' #,##0.00'})
        
        number_row = 1
        for line in order_sudo.porder_line.filtered(lambda self:self.qty_accepted>0 if self.porder_id.accepted else True):
            worksheet.set_row(number_row,98)
            if line.sudo().product_id.image_128:
                buf_image=io.BytesIO(base64.b64decode(line.sudo().product_id.image_128))
                worksheet.insert_image(xl_rowcol_to_cell(number_row, 0), "image.jpg", {'image_data': buf_image})
            worksheet.write(number_row, 1, '{}'.format(line['milor_code']))
            worksheet.write(number_row, 2, '{}'.format(line['barcode_text'] if line['barcode_text'] else ''))
            worksheet.write(number_row, 3, '{}'.format(line['category_name'] ))
            worksheet.write(number_row, 4, '{}'.format(line['name']))
            worksheet.write(number_row, 5, '{}'.format(line['weight_gr']))
            worksheet.write(number_row, 6, '{}'.format(line['length_cm']))
            worksheet.write(number_row, 7, '{}'.format(line['stone_color'] if line['stone_color'] else ''))
            
            worksheet.write(number_row, 8, '{}'.format(line['barcode']))
            worksheet.write(number_row, 9, '{}'.format(line['free_qty']))
            worksheet.write(number_row, 10, '{}'.format(line['default_code']))
            worksheet.write(number_row, 11, '{}'.format(line['retail_price']))
            
            
            worksheet.write(number_row, 12, (int(line['qty_proposed'])))
            worksheet.write(number_row, 13, (line['price_proposed']),money_format)
            worksheet.write(number_row, 14,(int(line['qty_accepted'])))
            worksheet.write(number_row, 15, (line['price_total_accepted']),money_format)
            worksheet.write(number_row, 16, '{}'.format(line['description'] or ''))
             
            if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
                worksheet.write(number_row, 17, '{}'.format(line['customer_product_code'] or ''))

            number_row += 1
        
        return worksheet
    
    def _generate_mto(self, worksheet=False, order_sudo=False,workbook=False):
        worksheet.set_column(0, 1, 18)
        worksheet.set_column(1, 2, 10)
        worksheet.set_column(2, 3, 30)
        
        
        worksheet.write(0, 0, 'Picture')
        worksheet.write(0, 1, 'Milor Reference')
        worksheet.write(0, 2, 'Title')
        worksheet.write(0, 3, 'Type')
        worksheet.write(0, 4, 'Description')
        worksheet.write(0, 5, 'Weight')
        worksheet.write(0, 6, 'Length')
        worksheet.write(0, 7, 'Color')
        worksheet.write(0, 8, 'Price')
        worksheet.write(0, 9, 'Quantity Accepted')
        worksheet.write(0, 10, 'Comments or changes')
        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.write(0, 11, 'Customer Product Code')
            
        money_format = workbook.add_format({'num_format': order_sudo.currency_id.symbol + ' #,##0.00'})

        number_row = 1
        for line in order_sudo.porder_line.filtered(lambda self:self.qty_accepted>0 if self.porder_id.accepted else True):
            worksheet.set_row(number_row,98)
            if line.sudo().product_id.image_128:
                buf_image=io.BytesIO(base64.b64decode(line.sudo().product_id.image_128))
                worksheet.insert_image(xl_rowcol_to_cell(number_row, 0), "image.jpg", {'image_data': buf_image})
            worksheet.write(number_row, 1, '{}'.format(line['milor_code']))
            worksheet.write(number_row, 2, '{}'.format(line['barcode_text'] if line['barcode_text'] else ''))
            worksheet.write(number_row, 3, '{}'.format(line['category_name']))
            worksheet.write(number_row, 4, '{}'.format(line['name']))
            worksheet.write(number_row, 5, '{}'.format(line['weight_gr']))
            worksheet.write(number_row, 6, '{}'.format(line['length_cm']))
            worksheet.write(number_row, 7, '{}'.format(line['stone_color'] if line['stone_color'] else ''))
            worksheet.write(number_row, 8, (line['price_proposed']),money_format)
            worksheet.write(number_row, 9, (int(line['qty_accepted'])))
            worksheet.write(number_row, 10, '{}'.format(line['description'] or ''))
            if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
                worksheet.write(number_row, 11, '{}'.format(line['customer_product_code'] or ''))

            number_row += 1
        
        return worksheet