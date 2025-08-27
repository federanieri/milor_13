# -*- coding: utf-8 -*-
import binascii
from datetime import date
from odoo.osv.expression import OR
from collections import OrderedDict

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.osv import expression


class CustomerPortal(CustomerPortal):

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='product', filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ]

        if bool(partner.is_agent and partner.selected_client_id):
            domain = [('state', 'in', ['sale', 'done']),('partner_id','=',partner.selected_client_id.id),('salesman_partner_id','=',partner.id)]
            
        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

        searchbar_inputs = {
            'name': {'input': 'name', 'label': _('Search in Name')},
            'product': {'input': 'product', 'label': _('Search in Products')}
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('delivery_status', 'in', ['to_deliver', 'partial', 'delivered'])]},
            'to_deliver': {'label': _('To Deliver'), 'domain': [('delivery_status', '=', 'to_deliver')]},
            'partial': {'label': _('Partially Delivered'), 'domain': [('delivery_status', '=', 'partial')]},
            'delivered': {'label': _('Delivered'), 'domain': [('delivery_status', '=', 'delivered')]},
            'to_deliver_partial': {'label': _('To Deliver & Partial'), 'domain': [('delivery_status', 'in', ['to_deliver','partial'])]},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('product'):
                search_domain = OR([search_domain, [('order_line.product_id.default_code', 'ilike', search)]])
            if search_in in ('name'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            domain += search_domain

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        archive_groups = self._get_archive_groups('sale.order', domain) if values.get('my_details') else []
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]


        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'filterby': filterby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = SaleOrder.search(domain, order=sort_order, offset=pager['offset'])[:self._items_per_page]
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("sale.portal_my_orders", values)
    
    def _prepare_home_portal_values(self):
        values = super(CustomerPortal, self)._prepare_home_portal_values()
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        quotation_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        
        if bool(partner.is_agent and partner.selected_client_id):
            order_count = SaleOrder.search_count([
                ('partner_id','=',partner.selected_client_id.id),
                ('salesman_partner_id','=',partner.id),
                ('state', 'in', ['sale', 'done'])
            ])
        else:
            order_count = SaleOrder.search_count([
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                ('state', 'in', ['sale', 'done'])
            ])

        values.update({
            'quotation_count': quotation_count,
            'order_count': order_count,
        })
        return values
    