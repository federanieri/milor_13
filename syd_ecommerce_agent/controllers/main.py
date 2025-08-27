# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.website_sale.controllers.main import WebsiteSale

class EcommerceAgentWebsiteSale(WebsiteSale):
    
    def _get_products_recently_viewed(self):
        
        if request.env.user.partner_id.selected_client_id:
            max_number_of_product_for_carousel = 12
            visitor = request.env['website.visitor']._get_visitor_from_request()
            if visitor:
                excluded_products = request.website.sale_get_order().mapped('order_line.product_id.id')
                products = request.env['website.track'].sudo().read_group(
                    [('visitor_id', '=', visitor.id), ('product_id', '!=', False), ('product_id.website_published', '=', True), ('product_id', 'not in', excluded_products)],
                    ['product_id', 'visit_datetime:max'], ['product_id'], limit=max_number_of_product_for_carousel, orderby='visit_datetime DESC')
                products_ids = [product['product_id'][0] for product in products]
                if products_ids:
                    viewed_products = request.env['product.product'].sudo().with_context(display_default_code=False).browse(products_ids)
    
                    FieldMonetary = request.env['ir.qweb.field.monetary']
                    monetary_options = {
                        'display_currency': request.website.get_current_pricelist().currency_id,
                    }
                    rating = request.website.viewref('website_sale.product_comment').active
                    res = {'products': []}
                    for product in viewed_products.filtered(lambda x: x.product_brand_id.id in request.env.user.partner_id.selected_client_id.product_brand_ids.ids ):
                        combination_info = product._get_combination_info_variant()
                        res_product = product.read(['id', 'name', 'website_url'])[0]
                        res_product.update(combination_info)
                        res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)
                        if rating:
                            res_product['rating'] = request.env["ir.ui.view"].render_template('website_rating.rating_widget_stars_static', values={
                                'rating_avg': product.rating_avg,
                                'rating_count': product.rating_count,
                            })
                        res['products'].append(res_product)
    
                    return res
            return {}
            
        else:
            res = super(EcommerceAgentWebsiteSale,self)._get_products_recently_viewed()
        return res
        
class EcommerceAgentController(CustomerPortal):
    
    
    @http.route('/set/partner/<int:partner_id>', type='http', auth="user", website=True)
    def set_partner(self, partner_id, **kw):
        if partner_id:
            partner_obj_id= request.env['res.partner'].browse(partner_id)
            partner = request.env.user.partner_id
            old_partner = partner.selected_client_id
            request.session['website_sale_current_pl'] = partner_obj_id.property_product_pricelist.id
            partner.selected_client_id = partner_id or request.env['res.partner']
            partner._reset_brand_group(old_partner, partner.selected_client_id)
            sale_order = request.website.sale_get_order(force_create=False)
            sale_order.order_line.unlink()
            if sale_order:
                sale_order.write({
                    'partner_id': partner_id,
                    'partner_invoice_id': partner_id,
                    'payment_term_id':partner_obj_id.property_payment_term_id.id
                })
        return request.redirect('/my/retailers')

    @http.route('/reset/partner', type='http', auth="user", website=True)
    def reset_partner(self, **kw):
        partner = request.env.user.partner_id
        old_partner = partner.selected_client_id
        partner.selected_client_id = False
        request.session['website_sale_current_pl'] = False
        partner._reset_brand_group(old_partner, request.env['res.partner'])
        return request.redirect('/my/retailers')

    @http.route(['/my/retailers', '/my/retailers/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_retailers(self, page=1, sortby=None, search=None,search_in='name',**kw):
        values = self._prepare_portal_layout_values()
        Partner = request.env['res.partner']
        partner = request.env.user.partner_id
        domain = [('id','in',partner.customer_of_salesman_ids.ids),('parent_id','=',False)]
        if search :
            domain +=  ['|', ('name', 'ilike', search), ('email', 'ilike', search)]
        

        searchbar_sortings = {
            'email': {'label': _('Email'), 'order': 'email asc'},
            'name': {'label': _('Reference'), 'order': 'name asc'},
        }
        searchbar_inputs = {
            'name': {'input': 'name', 'label': _('Search <span class="nolabel"> (in Name or Email)</span>')},
            
        }
        # default sort by order
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        # count for pager
        partner_count = Partner.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/retailers",
            url_args={'sortby': sortby},
            total=partner_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        partners = Partner.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_retailers_history'] = partners.ids[:100]

        values.update({
            'partners': partners,
            'page_name': 'retailer',
            'pager': pager,
            'default_url': '/my/retailers',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'selected_partner': request.env.user.partner_id.selected_client_id.id,
            'searchbar_inputs':searchbar_inputs,
            'search': search,
            'search_in': search_in
            
        })
        return request.render("syd_ecommerce_agent.portal_retailers_list", values)
