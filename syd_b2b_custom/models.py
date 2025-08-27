# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.osv import expression
import json
from odoo.http import request


    
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    commitment_date = fields.Datetime('Delivery Date',
                                      states={'sale': [('readonly', True)]},
                                      copy=False, readonly=False,
                                      help="This is the delivery date promised to the customer. "
                                           "If set, the delivery order will be scheduled based on "
                                           "this date rather than product lead times.")
    
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        values = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        line_id = values.get('line_id')

        for line in self.order_line:
            if line.product_id.type == 'product' and line.product_id.inventory_availability in ['sell_with_zero_stock']:
                cart_qty = sum(self.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                # The quantity should be computed based on the warehouse of the website, not the
                # warehouse of the SO.
                website = self.env['website'].get_current_website()
                if cart_qty > line.product_id.with_context(warehouse=website.warehouse_id.id).free_qty and (line_id == line.id):
                    

                    # Make sure line still exists, it may have been deleted in super()_cartupdate because qty can be <= 0
                    if line.exists():
                        line.warning_stock = _('Warning! For this product you have ordered more quantities than in stock, it will be delivered to you in about 30 days ')
                        values['warning'] = line.warning_stock
                    
        return values
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    thron_name = fields.Char('Thron Name',compute="_thron_field")
    thron_description = fields.Text('Thron Description',compute="_thron_field")
    inventory_availability = fields.Selection(selection_add=[
        ('sell_with_zero_stock', 'Show stock and sell regardless of inventory'),
           ])
    


    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        res = super(ProductTemplate,self)._get_combination_info(combination,product_id,add_qty,pricelist,parent_combination,only_template)
        product_id = self.env['product.product'].browse(res['product_id'])
        res.update({
                    'default_code':product_id.default_code,
                    'out_of_collection_variant':product_id.out_of_collection_variant,
                    'free_qty':product_id.sudo().free_qty,
                    'free_qty_formatted': self.env['ir.qweb.field.float'].value_to_html(product_id.sudo().free_qty, {'decimal_precision': 'Product Unit of Measure'}),
                    'arriving':product_id.sudo().free_qty == 0 and product_id.sudo().free_qty<product_id.virtual_available
                    })
        realpricelist = pricelist or (hasattr(request,'website') and request.website and request.website.get_current_pricelist())
        if not only_template:
            return res
        elif realpricelist:
            product_template_id = self.env['product.template'].browse(res['product_template_id'])
            min_price = 0
            for v in product_template_id.product_variant_ids.filtered(lambda self: self.out_of_collection_variant == False):
                price = realpricelist.price_get(v.id,1).get(realpricelist.id,0)
                if min_price == 0:
                    min_price = price
                elif price < min_price:
                    min_price = price
            if min_price:
                res['price']=min_price
        return res
    
    def _thron_field(self):
        lang = 'en'
        lang_complete = self.env.context['lang'] if 'lang' in self.env.context else False
        if lang_complete:
            lang = lang_complete.split('_')[0]
        for a in self:
            a.thron_name = a._get_meta_field('name_lang',lang)
            a.thron_description = a._get_meta_field('technical_description','it') if lang == 'it' else a._get_meta_field('plating_description','it')
            a.website_description = a._get_meta_field('technical_description','it') if lang == 'it' else a._get_meta_field('plating_description','it')
    
