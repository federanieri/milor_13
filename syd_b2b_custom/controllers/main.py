# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from werkzeug.exceptions import Forbidden, NotFound
from operator import itemgetter

from odoo import fields, http, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.tools import groupby as groupbyelem
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)



class WebsiteSaleCustom(WebsiteSale):

	@http.route('/shop/cart/product/autocomplete', type='json', auth='public', website=True)
	def cart_product_autocomplete(self, term, options={}, **kwargs):
		res = super(WebsiteSaleCustom,self).products_autocomplete(term,options,**kwargs)
		for res_product in res['products']:
				t = request.env['product.product'].browse(res_product['id'])
				res_product['name'] = t.name_composed
				
		return res
	
	@http.route('/shop/products/autocomplete', type='json', auth='public', website=True)
	def products_autocomplete(self, term, options={}, **kwargs):
		res = super(WebsiteSaleCustom,self).products_autocomplete(term,options,**kwargs)
		for res_product in res['products']:
				t = request.env['product.template'].browse(res_product['id'])
				
				res_product['name'] = t.name_composed
				
		return res
	
	def _get_search_domain(self, search, category, attrib_values,search_in_description=True, filter_values=False):
		domain = request.website.sale_product_domain()
		if search:
			for srch in search.split(" "):
				domain += [
					'|', '|', '|','|',  ('name_composed', 'ilike', srch), ('description', 'ilike', srch),
					('website_description', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch),('product_variant_ids.barcode', 'ilike', srch)]

		if category:
			domain += [('public_categ_ids', 'child_of', int(category))]

		if attrib_values:
			attrib = None
			ids = []
			for value in attrib_values:
				if not attrib:
					attrib = value[0]
					ids.append(value[1])
				elif value[0] == attrib:
					ids.append(value[1])
				else:
					domain += [('attribute_line_ids.value_ids', 'in', ids)]
					attrib = value[0]
					ids = [value[1]]
			if attrib:
				domain += [('attribute_line_ids.value_ids', 'in', ids)]


		if filter_values:
			filter = None
			
			for value in filter_values:
					fv = request.env['product.filter.value'].browse(value[1])
					domain += safe_eval(fv.filter_domain)
					

		return domain




	