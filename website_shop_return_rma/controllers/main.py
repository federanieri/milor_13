# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from collections import OrderedDict
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from odoo import http, _, tools
from odoo.addons.portal.controllers.portal import CustomerPortal as website_account
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.addons.stock_barcode.controllers.main import StockBarcodeController

class StockBarcodeControllerExt(StockBarcodeController):

    def try_open_picking(self, barcode):
        """ If barcode represents a picking, open it
        """
        
        ro = request.env['return.order'].search([
            ('number', '=', barcode),
        ], limit=1)
        if ro and ro.incoming_delivery_id :
                if ro.incoming_delivery_id.state == 'assigned':
                    return self.get_action(ro.incoming_delivery_id.id)
        
        
        return super(StockBarcodeControllerExt,self).try_open_picking(barcode)
    
    
class website_account(website_account):

    def _prepare_portal_layout_values(self): #odoo11
        values = super(website_account, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        rma_order = request.env['return.order']
        sale_order = request.env['sale.order']
        return_count = rma_order.sudo().search_count([
        ('partner_id', 'child_of', [partner.commercial_partner_id.id])
          ])
        return_or_sale_count = return_count + sale_order.sudo().search_count([
        ('partner_id', 'child_of', [partner.commercial_partner_id.id])
          ])
        values.update({
        'return_or_sale_count': return_or_sale_count,
        'return_count': return_count,
        })
        
        return values



    def _create_return_order_attachment(self, rma_order, kw): #odoo13
        return True
    
    
    @http.route(['/return/form'], type='http', auth="public", website=True)
    def portal_return_simple_form(self, **kw): 
                return request.render("website_shop_return_rma.form_return")
            
    @http.route(['/return/customer_form'], type='http', auth="user", website=True)
    def portal_return_form(self, **kw):
                return request.render("website_shop_return_rma.customer_form_return")
    
    @http.route(['/return/product_form'], type='http', auth="public", website=True)
    def portal_return_from_form(self, **kw): 
                vals = {
                            'origin' : tools.ustr(kw['reason']),
                            'email':tools.ustr(kw['email']),
                            'product_code':tools.ustr(kw['product_code']),
                            'quantity' :float(kw['quantity']),
                            'reason':tools.ustr(kw['reason']),
                            'origin':'form',
                            'return_type' : tools.ustr(kw['return_type']).lower(),
                        }
                if 'order_code' in kw:
                    vals['order_code']=tools.ustr(kw['order_code'])
                rec = request.env['return.order'].sudo().create(vals)
               
                return request.render("website_shop_return_rma.successful_return_from_form")
           
    
    @http.route(['/return/product'], type='http', auth="user", website=True)
    def portal_return(self, **kw):
        sale_order = request.env['sale.order'].sudo().browse(int(kw['order_id']))
        today_date = datetime.today().date()
        values = {
            'company': request.env.user.partner_id.company_id.name,
        }
        
        if today_date <= sale_order.return_date:
            sale_order_line = request.env['sale.order.line'].sudo().browse(int(kw['line_id']))
            quantity_validate = sale_order_line.product_uom_qty - sale_order_line.return_quantity
            float_value = 0.0
            float_value = float(kw['quantity'])
            if float_value <= quantity_validate and float_value != 0.0:
                return_quantadd = float_value + sale_order_line.return_quantity
                vals = {
                        'partner_id' : int(kw['partner_id']),
                        'saleorder_id':sale_order.id,
                        'saleorderline_id':sale_order_line.id,
                        'product_id':sale_order_line.product_id.id,
                        'quantity' :float(kw['quantity']),
                        'reason':tools.ustr(kw['reason']),
                        'delivery_method':tools.ustr(kw['delivery_method']),
                        'document_number':tools.ustr(kw['document_number']),
                        'document_date':tools.ustr(kw['document_date']),
                        'create_date' : fields.Date.today(),
#                        'company' : request.env.user.company_id.name, odoo13
                        'company_id' : request.env.user.company_id.id,
                        'return_by': request.env.user.id,
                        'create_date' : fields.Date.today(),
                        'return_type' : tools.ustr(kw['return_type']).lower(),
                                            }
                rec = request.env['return.order'].sudo().create(vals)
                attachment_id = self._create_return_order_attachment(rec, kw) #odoo13
                updateline = sale_order_line.write({'return_quantity' : return_quantadd,'return_rma_ids' : [(4, rec.id)]})
                values.update({
                    'return_id': rec,
                })
                return request.render("website_shop_return_rma.successful_return", values)
            else:
                return request.render("website_shop_return_rma.higher_quantity", values)
        else:
            return request.render("website_shop_return_rma.validity_expire", values)
            
    @http.route(['/my/returns'], type='http', auth="user",website=True)
    def portal_display_return(self, page=1,filterby=None,date_begin=None, date_end=None,sortby=None, **kw):
        response = super(website_account, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        return_obj = http.request.env['return.order']
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id])
        ]
        # count for pager
        return_count = return_obj.sudo().search_count(domain)
        searchbar_sortings = {
           'date': {'label': _('Newest'), 'order': 'create_date desc'},
           'name': {'label': _('Name'), 'order': 'number'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        sale_order_obj = request.env['sale.order'].sudo().search([])
        for sale_obj in sale_order_obj:
            searchbar_filters.update({
                str(sale_obj.id): {'label': sale_obj.name, 'domain': [('saleorder_id', '=', sale_obj.id)]}
            })
        return_obj.read_group([('saleorder_id', 'not in', sale_order_obj.ids)],
                                                                ['saleorder_id'], ['saleorder_id'])
        for group in return_obj:
            return_id = group['saleorder_id'][0] if group['saleorder_id'] else False
            return_name = group['saleorder_id'][1] if group['saleorder_id'] else _('Others')
            searchbar_filters.update({
                str(return_id): {'label': return_name, 'domain': [('saleorder_id', '=', return_id)]}
            })
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # pager
        pager = request.website.pager(
            url="/my/returns",
            total=return_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin, 'date_end': date_end,'sortby': sortby,'filterby': filterby},
        )

        
        # content according to pager and archive selected
        returns = return_obj.sudo().search(domain, limit=self._items_per_page, offset=pager['offset'],order=order)
       
        values.update({
            'returns': returns,
            'page_name': 'return',
            'pager': pager,
            'default_url': '/my/returns',
        })
        return request.render("website_shop_return_rma.display_returns", values)
