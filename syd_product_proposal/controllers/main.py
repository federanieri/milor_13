# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, get_records_pager
import re, tempfile, datetime, os, xlsxwriter, base64
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)
class CustomerPortal(CustomerPortal):
    
    @http.route(['/my/proposal_orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_proposal_orders_page(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('proposal.sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='syd_product_proposal.action_report_proposal_saleorder', download=download)

        if bool(report_type=='xls'):
            generated_excel = self.generate_excel(order_sudo)
            return request.redirect(generated_excel.get('url'))
            
        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if order_sudo:
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_proposal_%s' % order_sudo.id)
            if isinstance(session_obj_date, date):
                session_obj_date = session_obj_date.isoformat()
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_proposal_%s' % order_sudo.id] = now
                body = _('Proposal viewed by customer %s') % order_sudo.partner_id.name
                _message_post_helper(
                    "proposal.sale.order",
                    order_sudo.id,
                    body,
                    token=order_sudo.access_token,
                    message_type="notification",
                    subtype="mail.mt_note",
                    partner_ids=order_sudo.user_id.sudo().partner_id.ids,
                )

        values = {
            'proposal_sale_order': order_sudo,
            'message': message,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
            'report_type': 'html',
            'action': order_sudo._get_portal_return_action(),
        }
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id

        if order_sudo.state in ('draft', 'sent', 'cancel'):
            history = request.session.get('my_proposal_history', [])
        else:
            history = request.session.get('my_proposal_orders_history', [])
        values.update(get_records_pager(history, order_sudo))

        return request.render('syd_product_proposal.proposal_sale_order_portal_template', values)

    @http.route(['/my/proposal_orders/<int:order_id>/accept'], type='http', auth="public", website=True)
    def accept_portal_proposal_order(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('proposal.sale.order', order_id, access_token=access_token)
            
            date_form = kw.get('date_form')
            date_to = kw.get('date_to')
            proposal_line = {}
        
            for k, v in kw.items():
                if(k.startswith('priceaccepted') or k.startswith('qtyaccepted') or k.startswith('description') or k.startswith('customerpcode')) and k.split('_')[2] not in proposal_line:
                    proposal_line[(k.split('_')[2])] = {'price_accepted': 0.0, 'qty_accepted': 0.0,'description': False, 'customer_product_code': False}
                if k.startswith('priceaccepted'):
                    proposal_line[k.split('_')[2]].update({'price_accepted': float(v.replace(",","."))})
                elif k.startswith('qtyaccepted'):
                    proposal_line[k.split('_')[2]].update({'qty_accepted': float(v.replace(",","."))})
              
                if k.startswith('description'):
                    proposal_line[(k.split('_')[2])].update({'description': str(v).strip()})
                if k.startswith('customerpcode'):
                    proposal_line[(k.split('_')[2])].update({'customer_product_code': str(v).strip()})   
                    
            order_sudo.write({'date_deadline_from':date_form, 'date_deadline_to':date_to})
            for ol in order_sudo.porder_line.sudo():
                valus = proposal_line.get(str(ol.id))
                if bool(valus):
                    ol.with_context({'tracking_disable': False}).write(valus)
            order_sudo.write({'accepted': True})
        except (AccessError, MissingError) as e:
            _logger.error("%s"%(str(e)),exc_info=True)
            return request.redirect('/my')
        return request.redirect('/my/proposal_orders/%s' % order_id)

    @http.route(['/my/proposal_orders/<int:order_id>/refuse'], type='http', auth="public", website=True)
    def refuse_portal_proposal_order(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('proposal.sale.order', order_id, access_token=access_token)
            order_sudo.action_cancel()
        except (AccessError, MissingError):
            return request.redirect('/my')
        return request.redirect('/my/proposal_orders/%s' % order_id)
       
    # ----------------------------------- #
    def generate_excel(self, order_sudo):
        filename = '{}{}{}'.format('export',datetime.datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'),'.xlsx')
        path = os.path.join(tempfile.gettempdir(), filename)
        
        workbook = xlsxwriter.Workbook(path)
        
        worksheet = workbook.add_worksheet('Proposal')
        
        if(order_sudo['type'] == 'mto'):
            worksheet = self._generate_mto(worksheet, order_sudo.sudo(),workbook)
        elif(order_sudo['type']=='mts'):
            worksheet = self._generate_mts(worksheet, order_sudo.sudo(),workbook)
        
        workbook.close()
        file = open(path,'rb')
        
        vals = {'name':filename,
                'type':'binary',
                'public':True,
                'datas':base64.b64encode(file.read())
                }
        
        attachment_id =request.env['ir.attachment'].sudo().create(vals)
        file.close()
        
        return{
            'type':'ir.actions.act_url',
            'url':'/web/content/{}?download=true'.format(attachment_id.id),
            'target':'self'
            }
        
    def _generate_mts(self, worksheet=False, order_sudo=False,workbook=False):
        
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(1, 2, 20)
        worksheet.set_column(2, 3, 20)
        worksheet.set_column(3, 4, 20)
        worksheet.set_column(4, 5, 20)
        worksheet.set_column(5, 6, 20)
        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.set_column(6, 7, 20)
        
        worksheet.write(0, 0, 'Description')
        worksheet.write(0, 1, 'Quantity proposed')
        worksheet.write(0, 2, 'Price proposed')
        worksheet.write(0, 3, 'Quantity Accepted')
        worksheet.write(0, 4, 'Price Accepted')
        worksheet.write(0, 5, 'Price Total Accepted')
        worksheet.write(0, 6, 'Comments or changes')
        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.write(0, 7, 'Customer Product Code')
        
        number_row = 1
        for line in order_sudo.porder_line.filtered(lambda self:self.qty_accepted>0 if self.porder_id.accepted else True):
            worksheet.write(number_row, 0, '{}'.format(line['name']))
            worksheet.write(number_row, 1, '{}'.format(line['qty_proposed']))
            worksheet.write(number_row, 2, '{}'.format(line['price_proposed']))
            worksheet.write(number_row, 3, '{}'.format(line['qty_accepted']))
            worksheet.write(number_row, 4, '{}'.format(line['price_accepted']))
            worksheet.write(number_row, 5, '{}'.format(line['price_total_accepted']))
            worksheet.write(number_row, 6, '{}'.format(line['description']))
            if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
                worksheet.write(number_row, 7, '{}'.format(line['customer_product_code'] or ''))

            number_row += 1
        
        return worksheet
    
    def _generate_mto(self, worksheet=False, order_sudo=False,workbook=False):
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(1, 2, 10)
        worksheet.set_column(2, 3, 30)
        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.set_column(3, 4, 30)
        
        worksheet.write(0, 0, 'Products')
        worksheet.write(0, 1, 'Price Proposed')
        worksheet.write(0, 2, 'Quantity Accepted')
        worksheet.write(0, 3, 'Comments or changes')
        if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            worksheet.write(0, 4, 'Customer Product Code')
       
        number_row = 1
        for line in order_sudo.porder_line.filtered(lambda self:self.qty_accepted>0 if self.porder_id.accepted else True):
            worksheet.write(number_row, 0, '{}'.format(line['name']))
            worksheet.write(number_row, 1, '{}'.format(line['price_proposed']))
            worksheet.write(number_row, 2, '{}'.format(line['qty_accepted']))
            if(line['description']!=False):
                worksheet.write(number_row, 3, '{}'.format(line['description'] or ''))
            if request.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
                worksheet.write(number_row, 4, '{}'.format(line['customer_product_code'] or ''))

            number_row += 1
        
        return worksheet