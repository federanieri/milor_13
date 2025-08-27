# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary
from odoo.osv.expression import OR, AND


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['rfq_count'] = request.env['purchase.order'].search_count([
            ('state', 'in', ['sent'])
        ])
        return values
    
    def purchase_get_domain(self, search_in, search):
        domain = [('published_in_portal', '=', True)]
        if search and search_in:
            search_domain = []
            
            if search_in in ('name',):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
                
            domain += search_domain
        return domain
    
    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, status=None, extra_search=None, search=None, extra_search_in='personalized', search_in='name', limit_num=0, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']
        PurchaseOrderLine = request.env['purchase.order.line']

        domain = []

        archive_groups = self._get_archive_groups('purchase.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'date_approve desc, id desc'},
            'date_old': {'label': _('Oldest'), 'order': 'date_approve asc, id desc'},            
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        
        searchbar_inputs = {
            'name': {'input': 'name', 'label': _('Search in Name')},
        }

        extra_searchbar_inputs = {
            'personalized': {'input': 'personalized', 'label': _('Search in Personalized')}
        }
        
        number_input = {
            'limit': {'input': 'limit', 'label': _('Limit number per page')}
        }
        
        if not limit_num:
            limit_num = 0
        
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done'])]},
            'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
            'dot_com': {'label': _('Dot Com'), 'domain': [('commercehub_po', '!=', False)]},
            'to_download_txt': {'label': _('TXT To Download'), 'domain': [
                ('downloaded_txt', '=', False),
                ('has_txt_type', '=', 'txt1'),
                ('order_line.dis_task_id', '!=', False)
            ]},
            'to_download_stl': {'label': _('STL To Download'), 'domain': [
                ('downloaded_stl', '=', False),
                ('has_txt_type', '=', 'txt2'),
                ('order_line.dis_task_id', '!=', False)
            ]},
        }

        status_filters = {
            'all': {'label': _('All'), 'domain': [('received_status', 'in', ['to_receive', 'partial', 'received'])]},
            'open': {'label': _('New'), 'domain': ['|',('purchase_order_type','in',('rework_one','rework_two')),'&',('in_charge', '!=', True), ('received_status', '=', 'to_receive'), ('spedito_da_fornitore', '!=', True), ('spedito_in_galvanica', '!=', True), ('downloaded_txt', '!=', True), ('downloaded_stl', '!=', True)]},
            'to_receive': {'label': _('In Charge'), 'domain': [('received_status', '=', 'to_receive'), ('in_charge', '=', True)]},
            'spedito': {'label': _('Spedito da Fornitore'), 'domain': [('spedito_da_fornitore', '=', True)]},
            'galvanica': {'label': _('Spedito in Galvanica'), 'domain': [('spedito_in_galvanica', '=', True)]},
            'downloaded_txt': {'label': _('TXT Scaricato'), 'domain': [('downloaded_txt', '=', True)]},
            'downloaded_stl': {'label': _('STL Scaricato'), 'domain': [('downloaded_stl', '=', True)]},
            'partial': {'label': _('Partially Delivered'), 'domain': [('received_status', '=', 'partial')]},
            'received': {'label': _('Delivered'), 'domain': [('received_status', '=', 'received')]},
        }

        if not status:
            status = 'all'
        domain += status_filters[status]['domain']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # search
        domain += self.purchase_get_domain(search_in,search)

        # extra-search
        if extra_search_in in ('personalized',) and extra_search:
            extra_domain = [('custom_value', 'ilike', extra_search)]
            extra_oids = PurchaseOrderLine.search(extra_domain).order_id
            domain += AND([domain, [('id', 'in', extra_oids.ids)]])

        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)

        # make pager
        pager = portal_pager(
            url="/my/purchase",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'status': status, 'sortby': sortby, 'extra_search_in': extra_search_in, 'search_in': search_in, 'extra_search': extra_search, 'search': search, 'filterby': filterby, 'limit_num':limit_num},
            total=purchase_count,
            page=page,
            step=int(limit_num) or self._items_per_page
        )

        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=int(limit_num) or self._items_per_page,
            offset=pager['offset']
        )

        request.session['my_purchases_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'purchase',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'extra_searchbar_inputs': extra_searchbar_inputs,
            'searchbar_inputs': searchbar_inputs,
            'number_input':number_input,
            'limit_num':limit_num,
            'extra_search_in': extra_search_in,
            'search_in': search_in,
            'extra_search': extra_search,
            'search': search,
            'status': status,
            'status_filters':status_filters,
            'default_url': '/my/purchase',
        })
        return request.render("purchase.portal_my_purchase_orders", values)

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, report_type=None,  access_token=None, download=False, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type and report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='purchase.action_report_purchase_order', download=download)
        return super(CustomerPortal,self).portal_my_purchase_order(order_id=order_id,access_token=access_token,**kw)
    
    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfqs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None,search=None, search_in='name', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']

        domain = []

        archive_groups = self._get_archive_groups('purchase.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['sent'])]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # search
        domain += self.purchase_get_domain(search_in,search)
        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/rfq",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=purchase_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_purchases_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'rfq',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/rfq',
        })
        return request.render("purchase.portal_my_purchase_orders", values)
