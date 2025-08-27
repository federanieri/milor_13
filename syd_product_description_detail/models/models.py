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
from odoo.tools.translate import html_translate


    
class ProductCategory(models.Model):
    _inherit = "product.category"
    
    fields_to_purchase = fields.Many2many('ir.model.fields','category_purchase_field','categ_id','field_id',string="Field for Purchase",domain="[('model','=','product.product')]")
    fields_to_sale = fields.Many2many('ir.model.fields','category_sale_field','categ_id','field_id',string="Field for Sale",domain="[('model','=','product.product')]")
    fields_to_website = fields.Many2many('ir.model.fields','category_website_field','categ_id','field_id',string="Field for Website",domain="[('model','=','product.template')]")
    fields_to_name = fields.Many2many('ir.model.fields','category_name_field','categ_id','field_id',string="Field for Name",domain="[('model','=','product.template')]")

    def _get_purchase_fields(self):
        def _get_category_purchase_fields(self):
            if not self.fields_to_purchase and self.parent_id:
                return _get_category_purchase_fields(self.parent_id)
            elif self.fields_to_purchase:
                return self.fields_to_purchase
            else:
                return self.env['ir.model.fields']
        self.ensure_one()
        return _get_category_purchase_fields(self)
            
    def _get_sale_fields(self):
        def _get_category_sale_fields(self):
            if not self.fields_to_sale and self.parent_id:
                return _get_category_sale_fields(self.parent_id)
            elif self.fields_to_sale:
                return self.fields_to_sale
            else:
                return self.env['ir.model.fields']
        self.ensure_one()
        return _get_category_sale_fields(self)
    
    def _get_website_fields(self):
        def _get_category_website_fields(self):
            if not self.fields_to_website and self.parent_id:
                return _get_category_website_fields(self.parent_id)
            elif self.fields_to_website:
                return self.fields_to_website
            else:
                return self.env['ir.model.fields']
        self.ensure_one()
        return _get_category_website_fields(self)
    
    
    def _get_name_fields(self):
        def _get_category_name_fields(self):
            if not self.fields_to_name and self.parent_id:
                return _get_category_name_fields(self.parent_id)
            elif self.fields_to_name:
                return self.fields_to_name
            else:
                return self.env['ir.model.fields']
        self.ensure_one()
        return _get_category_name_fields(self)
     
    def update_descriptions(self):
        for a in self:
           products = self.env['product.product'].search([('categ_id','child_of',a.id)])
           for p in products:
               p.sudo()._set_description_purchase()
               p.sudo()._set_description_sale()
               
           templates = self.env['product.template'].search([('categ_id','child_of',a.id)])
           for p in templates:
               p.sudo()._set_name_website()
               p.sudo()._set_description_website()
               
class ProductTemplate(models.Model):
    _inherit = "product.template"

    name_composed = fields.Char('Name Composed',translate=True)
    product_description = fields.Html('Product Description', sanitize_attributes=False, translate=html_translate, help="A description or specification of this Product that you want to communicate to your customers.")
    
    def write(self,values):
        res = super(ProductTemplate,self).write(values)
        if not self.env.context.get('no_recall',False):
            for a in self:
                a.sudo()._set_name_website()
                a.sudo()._set_description_website()
        return res
    
    def _set_name_website(self):
        for lang in ['it_IT','en_US']:
            for a in self.with_context(lang=lang):
                if a.categ_id:
                    fields = a.categ_id._get_name_fields()
                    name_string = ''
                    for f in fields:
                        if getattr(a,f.name):
                            
                            name_string +='%s ' % (getattr(a,f.name).display_name if f.relation  else getattr(a,f.name))
                            
                    if name_string:
                        a.with_context(no_recall=True).write({'name_composed':name_string})
    
    def _set_description_website(self):
        for lang in ['it_IT','en_US']:
            for a in self.with_context(lang=lang):
                if a.categ_id:
                    fields = a.categ_id._get_website_fields()
                    sale_string = ''
                    for f in fields:
                        if getattr(a,f.name):
                            
                            sale_string +='%s:%s <br />' % (f.field_description,getattr(a,f.name).display_name if f.relation  else getattr(a,f.name))
                            
                    if sale_string:
                        a.with_context(no_recall=True).write({'website_description':sale_string})
        

class ProductProduct(models.Model):
    _inherit = "product.product"
    
    description_purchase = fields.Text('Description Purchase',translate='True')
    description_sale = fields.Text('Description Sale',translate='True')
    
    
    
    
    def write(self,values):
        res = super(ProductProduct,self).write(values)
        if not self.env.context.get('no_recall',False):
            for a in self:
                a.sudo()._set_description_purchase()
                a.sudo()._set_description_sale()
                
                
        return res
                
    def _set_description_purchase(self):
        for lang in ['it_IT','en_US']:
            for a in self.with_context(lang=lang):
                if a.categ_id:
                    fields = a.categ_id._get_purchase_fields()
                    purchase_string = ''
                    for f in fields:
                        if getattr(a,f.name):
                            purchase_string +='%s:%s \n' % (f.field_description,getattr(a,f.name).display_name if f.relation  else getattr(a,f.name))
                    if purchase_string:
                        a.with_context(no_recall=True).write({'description_purchase':purchase_string})
                    
    def _set_description_sale(self):
        for lang in ['it_IT','en_US']:
            for a in self.with_context(lang=lang):
                if a.categ_id:
                    fields = a.categ_id._get_sale_fields()
                    sale_string = ''
                    for f in fields:
                        if getattr(a,f.name):
                            sale_string +='%s:%s \n' % (f.field_description,getattr(a,f.name).display_name if f.relation  else getattr(a,f.name))
                    if sale_string:
                        a.with_context(no_recall=True).write({'description_sale':sale_string})
                    
    
   
                        