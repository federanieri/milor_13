# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from ast import literal_eval

from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang
from odoo.tools.safe_eval import safe_eval

class Pricelist(models.Model):
    _inherit = "product.pricelist"
    
    def _compute_price_rule_get_items(self, products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids):
        items = super(Pricelist,self)._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)
        res = []
        for i in items:
            if i.applied_on == '00_filter':
                p_ids = self.env['product.product'].browse(prod_ids)
                if p_ids.filtered_domain(literal_eval(i.domain)):
                    res.append(i)
            else:
                res.append(i)
        return res
    
class PricelistItem(models.Model):
    _inherit = ["product.pricelist.item"]
    
    domain = fields.Text(default='[]', required=True)
    model_id = fields.Char(string='Model',default="product.product")
     
    applied_on = fields.Selection(selection_add=[('00_filter', 'Filter')])

    
    
        
    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        super(PricelistItem, self)._get_pricelist_item_name_price()
        for item in self:
            if item.applied_on == '00_filter' and item.model_id:
                if item.model_id == 'product.product':
                    item.name = _("Variant Filter: %s") % (item.domain)
                


    def _compute_price(self, price, price_uom, product, quantity=1.0, partner=False):
        if self.applied_on == '00_filter':
            if self.model_id == 'product.product':
                product = product.filtered(lambda p: p.filtered_domain(literal_eval(self.domain)))
                if not product.exists():
                    return price
        return super(PricelistItem, self)._compute_price(price, price_uom, product, quantity=1.0, partner=False)



