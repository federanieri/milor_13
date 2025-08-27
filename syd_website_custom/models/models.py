# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import re

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    product_brand_id = fields.Char(string='Brand', related="product_id.product_brand_id.name")
     
    @api.model
    def create(self, vals_list):
        res = super(SaleOrderLine, self).create(vals_list)
        if not bool(self.env.context.get('stop_loop',False)) and not vals_list.get('is_delivery'):
            res.order_id.return_ordered_sol()  
        return res
                 
    
class SaleOrders(models.Model):
    _inherit = "sale.order"

    def return_ordered_sol(self):
        if (self.create_uid.id == 1) and bool(self.order_line):
            seq = sorted([ol.sequence for ol in self.order_line])[0]
            for num, ol in enumerate(self.order_line.sorted(key=lambda r: r.product_brand_id or '')):
                self.order_line.browse(ol.id).with_context(stop_loop=True).write({'sequence':seq + num })
     
class productProduct(models.Model):
    _inherit = "product.product"
    
    weight_gr = fields.Float(compute='_compute_weight_gr', store=True, readonly=False) 

    @api.depends('bom_ids.bom_line_ids','bom_ids.bom_line_ids.product_id.weight_gr','bom_ids.bom_line_ids.product_qty')
    def _compute_weight_gr(self):
        for a in self:
            a.weight_gr = 0.0
            bom_id = a.bom_ids.filtered(lambda x: x.product_id.id == a.id or (x.product_tmpl_id.id == a.product_tmpl_id.id and not x.product_id.id))
            if bool(bom_id.bom_line_ids):
                a.weight_gr = sum((bom_line.product_qty * bom_line.product_id.weight_gr) for bom_line in bom_id.bom_line_ids)

class productTemplate(models.Model):
    _inherit = "product.template"
    
    def _remove_internal_ref(self):
        if isinstance(self.website_description, str):
            return re.sub(r"([i|I]nternal.[r|R]eference:.*?<br>)","",self.website_description)
        else:
            return self.website_description
        
    def _get_filtered_image(self, domain=None):
        """
            Únicamente utilizar los que tengan más de un material porque las fotos serán diferentes
        """
        variant = self.product_variant_ids.filtered(lambda x: x.plating_id.display_name == domain[2])
        if variant and len(self.product_variant_ids) != len(variant):
            return variant[0] if len(variant) > 1 else variant
        else:
            return False