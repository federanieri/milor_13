# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import get_lang
from odoo import api, fields, models, _
from werkzeug.urls import url_encode
from collections import defaultdict
from odoo.tools.safe_eval import safe_eval

class CommonProductBrandEpt(models.Model):
    _inherit = 'common.product.brand.ept'
    
    barcode_text = fields.Char('Barcode Text')

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    barcode_text = fields.Char('Barcode Text',related="product_brand_id.barcode_text")
       
class ProposalSaleOrderLine(models.Model):
    _inherit = "proposal.sale.order.line"
    _order = 'category_name'
    category_name=fields.Char('Type',related="product_id.categ_id.name",store=True)
    
    milor_code = fields.Char('Milor code',related="product_id.milor_code")
    
    default_code = fields.Char('Milor code',related="product_id.default_code")
    barcode = fields.Char('Barcode',related="product_id.barcode")
    free_qty = fields.Float('Free Qty',related="product_id.free_qty")
    retail_price = fields.Float('Retail Price',related="product_id.lst_price")
    
    weight_gr = fields.Float('Weight (gr)',related="product_id.weight_gr")
    barcode_text = fields.Char('Title',related="product_id.barcode_text")
    length_cm = fields.Char('Length(cm)',compute="_length")
    stone_color = fields.Char('Color',related="product_id.stone_color")
    
    def _length(self):
        for a in self:
            length = ''
            for b in a.product_id.product_template_attribute_value_ids:
                
                if length != '':
                    length+=", "
                length += '%s:%s'%(b.attribute_id.name,b.name)
            a.length_cm = length

    