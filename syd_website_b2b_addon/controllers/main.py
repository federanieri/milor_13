# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.osv import expression


class WebsiteB2BAddon(WebsiteSale):

    @http.route(['/my/reorder'], type='http', auth="user", website=True)
    def portal_sale_reorder(self, access_token=None, **post):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        # TODO: check for the delivery charge products
        original_sale_order = request.env['sale.order'].sudo().browse(int(post.get('sale_id'))).exists()
        for line in original_sale_order.order_line:
            if not len(sale_order.order_line):
                line.copy(default={'order_id': sale_order.id})
            else:
                order_line = sale_order._cart_find_product_line(line.product_id.id)[:1]
                if order_line:
                    order_line.product_uom_qty += line.product_uom_qty
                else:
                    line.copy(default={'order_id': sale_order.id})
        return request.redirect("/shop/cart")
    
    @http.route('/shop/cart/product/autocomplete', type='json', auth='public', website=True)
    def cart_product_autocomplete(self, term, options={}, **kwargs):
        """
        Returns list of products according to the term and product options

        """
        Product = request.env['product.product']
        order = self._get_search_order(options)
        domain = self._get_search_domain(term, category=False, attrib_values=False)
        products = Product.search(
            domain,
            limit=min(20, options.get('limit', 5)),
            order=order
        )
        fields = ['id', 'name', 'default_code']
        res = {
            'products': products.read(fields),
            'products_count': Product.search_count(domain),
        }

        return res
    
    
    
    def _get_search_domain(self, search, category, attrib_values, search_in_description=True):
        """Override in order to allow search product by barcode"""
        domains = super(WebsiteB2BAddon, self)._get_search_domain(search, category, attrib_values, search_in_description)
        if search:
            subdomains = [('barcode', 'ilike', search)]
            domains = expression.OR([domains, subdomains])
        return domains


