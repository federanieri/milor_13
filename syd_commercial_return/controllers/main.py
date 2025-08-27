# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.osv import expression
from odoo.http import request
from collections import OrderedDict
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from odoo import http, _, tools
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, date
from odoo import api, fields, models, _
from odoo.addons.stock_barcode.controllers.main import StockBarcodeController
from odoo.addons.base.models.ir_ui_view import keep_query


class StockBarcodeControllerExt(StockBarcodeController):

    def try_open_picking(self, barcode):
        """ If barcode represents a picking, open it
        """
        
        ro = request.env['return.order.sheet'].search([
            ('number', '=', barcode),
        ], limit=1)
        if ro :
            for corresponding_picking in ro.picking_ids.filtered(lambda r: r.picking_type_id.code == 'incoming' and r.state in ['assigned']):
                    return self.get_action(corresponding_picking.id)
        
        
                    
        return super(StockBarcodeControllerExt,self).try_open_picking(barcode)
class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self): #odoo11
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        rma_order = request.env['return.order.sheet']
        
        return_count = rma_order.sudo().search_count([
        ('partner_id', 'child_of', [partner.commercial_partner_id.id])
          ])
        values.update({
        'has_commercial_return': partner and partner.has_commercial_return,
        'return_sheet_count': return_count,
        })
        
        return values

    @http.route(['/commercial_return_line/delete'], type='http', auth="user",website=True)
    def portal_commercial_return_line_delete(self, **kw):
        if bool(kw['line_id']):
            line_id = request.env['return.order.line'].sudo().browse(int(kw['line_id']))
            return_order_sheet_id = line_id.return_order_sheet_id.id
            line_id.unlink()

        sale_order = kw['sale_order'] if 'sale_order' in kw else None
        values= {
            'creturn': request.env['return.order.sheet'].sudo().browse(return_order_sheet_id),
            'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
            'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id
        }
        if bool(sale_order):
            return request.redirect('/return/%s?order_id=%s&%s' % (values['creturn'].id, sale_order, keep_query('access_token')))

        return request.render("syd_commercial_return.return_order_sheet", values)
    
    
    @http.route(['/commercial_return/confirm'], type='http', auth="user",website=True)
    def portal_commercial_return_confirm(self, **kw):
        creturn_id = request.env['return.order.sheet'].sudo().browse(int(kw['return_order_sheet_id']))
        creturn_id.action_sent()
        values= {
            'creturn': request.env['return.order.sheet'].sudo().browse(int(kw['return_order_sheet_id'])),
            'message' : 'Commercial return is sent'
        }
        return request.render("syd_commercial_return.return_order_sheet", values)
           

    @http.route(['/commercial_return/<int:order_id>', '/commercial_return/<int:order_id>/<int:sale_order>'], type='http', auth="user",website=True)
    def portal_commercial_return_show(self, order_id=None, sale_order=None, **kw):
        
        values= {
            'creturn': request.env['return.order.sheet'].sudo().browse(order_id),
            'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
            'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id
        }

        if bool(sale_order) and values['creturn'].state in ['draft']:
            values['sale_order'] = request.env['sale.order'].browse(sale_order)
            return request.render("syd_commercial_return.display_products_to_return", values)
        
        return request.render("syd_commercial_return.return_order_sheet", values)
        
    
    @http.route(['/commercial_return/new'], type='http', auth="user", website=True)
    def portal_commercial_return_new(self, **kw):
        
        today_date = datetime.today().date()
        values = {
            'partner_id': request.env.user.partner_id.id,
            'return_type' :tools.ustr(kw['return_type']),
            'from_web':True
        }
        creturn = request.env['return.order.sheet'].sudo().create(values) 
        
        if bool(kw.get('sale_order')):
            return request.redirect('/return/%s?order_id=%s&%s' % (creturn.id, kw.get('sale_order'), keep_query('access_token')))
            
        values.update({
            'creturn': creturn,
            'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
            'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id
        })
        return request.render("syd_commercial_return.return_order_sheet", values)
#
    
    
    @http.route(['/commercial_return_line/add_barcode'], type='http', auth="user",website=True)
    def portal_commercial_return_line_fast_save(self, **kw):
        product_code = tools.ustr(kw['product_code'])
        product_id = request.env['product.product'].sudo().search(['|',('default_code','=',product_code),('barcode','=',product_code)],limit=1)
        return_order_sheet_id = int(kw['return_order_sheet_id'])
        values= {
            'creturn': request.env['return.order.sheet'].sudo().browse(int(kw['return_order_sheet_id'])),
            'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
            'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id
        }
        if not product_id:
            values['error'] = 'Product does not exist'
            return request.render("syd_commercial_return.return_order_sheet", values)
        line = request.env['return.order.line'].search([('product_id','=',product_id.id),('return_order_sheet_id','=',return_order_sheet_id)],limit=1)
        if line:
            line.quantity += 1
        else:
            vals = {
                            'product_id' : product_id.id,
                            'return_order_sheet_id' : int(kw['return_order_sheet_id']),
                            'quantity' :1,
                            'product_code':product_code
                            
                    }
            request.env['return.order.line'].sudo().create(vals) 
        
        return request.render("syd_commercial_return.return_order_sheet", values)
    
    @http.route(['/commercial_return_line/save'], type='http', auth="user",website=True)
    def portal_commercial_return_line_save(self, **kw):
        product_code = tools.ustr(kw['product_code']) if 'product_code' in kw else False
        sale_code = tools.ustr(kw['sale_code']) if 'sale_code' in kw else False
        sale_order = kw.get('sale_order') if 'sale_order' in kw else False
        product_id = request.env['product.product'].sudo().search(['|',('default_code','=',product_code),('barcode','=',product_code)],limit=1)
        return_order_sheet_id = int(kw['return_order_sheet_id'])
        values= {
            'creturn': request.env['return.order.sheet'].sudo().browse(int(kw['return_order_sheet_id'])),
            'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
            'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id
        }
        if not product_id:
            values['error'] = 'Product does not exist'
            return request.render("syd_commercial_return.return_order_sheet", values)
        
        line = request.env['return.order.line'].search([('product_id','=',product_id.id),('return_order_sheet_id','=',return_order_sheet_id)],limit=1)
        closing_text_id = [key for key in kw.keys() if 'closing_text' in key]
        if bool(closing_text_id):
            closing_text_id = closing_text_id[0]    
        if line:
            line.write({
                        'quantity' :line.quantity + float(kw['quantity']),
                        'reason': request.env['return.order.reason'].sudo().browse(int(kw.get('reason'))).id
                        })
            
            if kw.get(closing_text_id) and bool(values['other_reason_id'] == int(kw.get('reason'))):
                line.write({
                    'specify_reason':tools.ustr(kw[closing_text_id]),
                })
        else: 
            vals = {
                            'product_id' : product_id.id,
                            'return_order_sheet_id' : int(kw['return_order_sheet_id']),
                            'quantity' :float(kw['quantity']),
                            'reason':request.env['return.order.reason'].sudo().browse(int(kw.get('reason'))).id,
                            'specify_reason':tools.ustr(kw[closing_text_id]) if bool(kw.get(closing_text_id)) and bool(values['other_reason_id'] == int(kw.get('reason'))) else False,
                            'product_code':product_code,
                            'sale_code':sale_code
                            
                    }
            request.env['return.order.line'].sudo().create(vals) 
            
        if bool(sale_order):
            return request.redirect('/return/%s?order_id=%s&%s' % (values['creturn'].id, sale_order, keep_query('access_token'))) #kw.get('access_token')
        else:
            return request.render("syd_commercial_return.return_order_sheet", values)
                 
    @http.route(['/my/commercial_returns','/my/commercial_returns/<int:order_id>'], type='http', auth="user",website=True)
    def portal_commercial_return(self, page=1,filterby=None,date_begin=None, date_end=None,sortby=None,order_id=None, **kw):
        response = super(CustomerPortal, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        return_obj = http.request.env['return.order.sheet']
        domain = [
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ]
        if bool(request.env.user.partner_id.is_agent): 
            domain = expression.OR([domain,[('partner_id','=',request.env.user.partner_id.selected_client_id.id),('salesman_partner_id','=',request.env.user.partner_id.id)]])
            
        if bool(order_id):
            domain = [('return_order_line_ids.sale_code','ilike',request.env['sale.order'].browse(order_id).name)]
        
        # count for pager
        return_count = return_obj.sudo().search_count(domain)
        searchbar_sortings = {
           'date': {'label': _('Newest'), 'order': 'create_date desc'},
           'name': {'label': _('Name'), 'order': 'number'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        
        
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
 
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # pager
        pager = request.website.pager(
            url="/my/commercial_returns",
            total=return_count,
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin, 'date_end': date_end,'sortby': sortby,'filterby': filterby},
        )
         
        # content according to pager and archive selected
        returns = return_obj.sudo().search(domain, limit=self._items_per_page, offset=pager['offset'],order=order)
        types = request.env['return.order.sheet']._fields['return_type'].selection
        types = request.env['return.order.sheet']._fields['return_type']._description_selection(request.env)
        values.update({
            'creturns': returns,
            'page_name': 'return_sheet',
            'pager': pager,
            'default_url': '/my/commercial_returns',
            'types':types,
            'from_so':request.env['sale.order'].browse(order_id) if bool(order_id) else None
        })
        return request.render("syd_commercial_return.display_sheet_returns", values)

    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        response = super(CustomerPortal, self).portal_order_page(order_id, report_type, access_token, message, download, **kw)
        types = request.env['return.order.sheet']._fields['return_type'].selection
        types = request.env['return.order.sheet']._fields['return_type']._description_selection(request.env)
        response.qcontext['types'] = types
        response.qcontext['rco'] = request.env['return.order.line'].search([('sale_code','ilike',request.env['sale.order'].browse(order_id).name)]).return_order_sheet_id
        return response
  
    @http.route(['/return','/return/<int:creturn_id>'], type='http', auth="user",website=True)
    def portal_commercial_return_extend(self, order_id, creturn_id=None, **kw):
        if not bool(creturn_id):
            values = {
                'partner_id': request.env.user.partner_id.id,
                'return_type' :tools.ustr(kw['return_type']),
                'from_web':True
            }
            creturn = request.env['return.order.sheet'].sudo().create(values) 
            
            return request.redirect('/return/%s?order_id=%s&%s' % (creturn.id, order_id, keep_query('access_token')))
        else:
            values = {
                'creturn': request.env['return.order.sheet'].sudo().browse(creturn_id),
                'partner_id': request.env.user.partner_id.id,
                'from_web':True,
                'reasons': request.env['return.order.reason'].sudo().search([]).sorted(key = lambda r: r.create_date, reverse=True),
                'other_reason_id': request.env.ref('syd_commercial_return.reason_type_other').id,
                'sale_order': request.env['sale.order'].browse(int(order_id))
            }
            
            return request.render("syd_commercial_return.display_products_to_return", values)
       
