# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteVariantGrid(WebsiteSale):

    @http.route('/shop/fetch/product/matrix', type='json', auth='public', website=True)
    def get_product_matrix(self, productTemplateId=False):
        return self._get_product_matrix(productTemplateId)

    def _get_product_matrix(self, productTemplateId=False):
        template = request.env['product.template'].browse(int(productTemplateId)).exists()
        if len(template.product_variant_ids) > 1:
            matrix = template._get_template_matrix()
        else:
            matrix = {}
        return matrix

    @http.route('/shop/apply/product/matrix', type='json', auth='public', website=True)
    def apply_product_matrix(self, productTemplateId=False, matrix=None):
        return self._apply_product_matrix(productTemplateId, matrix)

    def _apply_product_matrix(self, productTemplateId, matrix=None):
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        Attributes = request.env['product.template.attribute.value']
        product_template = request.env['product.template'].browse(int(productTemplateId)).exists()
        for cell in matrix:
            combination = Attributes.browse(cell['ptav_ids'])
            # create or find product variant from combination
            if cell['qty']>0:
                product = product_template._create_product_variant(combination)
                sale_order._cart_update(
                    product_id=product.id,
                    add_qty=cell['qty'],
                )
        return True

