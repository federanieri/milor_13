# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
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
_logger = logging.getLogger('Shopify Milor')

class res_partner(models.Model):
    _inherit = "res.partner"
    
    
    @api.model
    def create_or_update_customer(self, vals, log_book_id, is_company=False, parent_id=False, type=False,
                                  instance=False, email=False, customer_data_queue_line_id=False,
                                  order_data_queue_line=False):
        
        res = super(res_partner,self).create_or_update_customer(vals, log_book_id, is_company, parent_id, type,
                                  instance, email, customer_data_queue_line_id,
                                  order_data_queue_line)
        res.write({'web_customer':True})
        if instance:
            res.write({'property_product_pricelist':instance.shopify_pricelist_id.id})
        return res
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    exclude_shopify_update = fields.Boolean('Exclude Shopify Align',compute="_exclude_shopify_update")
    
    def _exclude_shopify_update(self):
        for a in self:
            a.exclude_shopify_update = bool(a.product_of_package_ids)
    
    
    
class ProductImageEpt(models.Model):
    _inherit = 'common.product.image.ept'


    # NomeProdotto (trattini)_Categoria (trattini)_Megacolor_1.jpg
    def _get_image_name(self,instance=False):
        if not instance:
            return False
        product = self.product_id
        product_tmpl_id = product.product_tmpl_id or self.template_id
        name = product_tmpl_id._get_meta_field('name_lang',instance.lang)
        if name:
            name=  name.replace(" ","-")
        else :
            name = ''
        category = product.categ_id.megacategory.lower() if product.categ_id.megacategory else ''
        if category:
            category = category.replace(" ","-")
                   
        stones = set()
        megacolor = ""
        for s in product.stone_ids:
                stones.add(s.id)
        for sid in stones:
                s = self.env['product.stone'].browse(sid)
                if s.megacolor_id:
                    megacolor += (s.megacolor_id.name.lower() if s.megacolor_id.name else '')
        megacolor = megacolor.replace(" ","-")
        arr = self.name.split("_")
        count = ""
        if len(arr)>1:
            count = "_%s" % (arr[len(arr)-1])
        newname = "%s_%s_%s%s" % (name,category,megacolor,count) 
        if name or category or megacolor or count:
            return newname                   
        return self.name
    
    
    
class Product(models.Model):
    _inherit = "product.product"
    
    def get_stock_ept(self, product_id, warehouse_id, fix_stock_type=False, fix_stock_value=0,
                      stock_type='virtual_available'):
        res = super(Product,self).get_stock_ept(product_id,warehouse_id,fix_stock_type,fix_stock_value,stock_type)
        if res> 5.00:
            return res-5.00
        else:
            return 0.00
    
    def get_free_qty(self, warehouse, product_list):
        """
        This method is return On hand quantity based on warehouse and product list
        @author:Krushnasinh Jadeja
        :param warehouse: warehouse object
        :param product_list: list of product object
        :return:On hand quantity
        """
        # locations = self.env['stock.location'].search(
        #     [('location_id', 'child_of', warehouse.lot_stock_id.id)])
        locations = self.env['stock.location'].search(
                 [('location_id', 'child_of', warehouse.mapped('lot_stock_id').mapped('id')),('stock_ubication','=',True)])
        location_ids = ','.join(str(e) for e in locations.ids)
        product_list_ids = ','.join(str(e) for e in product_list.ids)
        # Query Updated by Udit
        qry = """select pp.id as product_id,
                COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock
                from product_product pp
                left join stock_quant sq on pp.id = sq.product_id and
                sq.location_id in (%s)
                where pp.id in (%s) group by pp.id;""" % (location_ids, product_list_ids)
        self._cr.execute(qry)
#         _logger.info(qry)
        On_Hand = self._cr.dictfetchall()
        dict_on_hand = {}
        for item in On_Hand:
            dict_on_hand[item['product_id']] = item['stock']
        return dict_on_hand

class ShopifyProductTemplateEpt(models.Model):
    _inherit = "shopify.product.template.ept"
    
    thron_message = fields.Char('Thron Message',compute="_thron_message",store=True) 
    
    @api.depends('product_tmpl_id.name_lang','shopify_product_ids.shopify_image_ids','product_tmpl_id.technical_description','product_tmpl_id.plating_description')
    def _thron_message(self):
        
        for t in self:
            thron_message = ''
            
            if not t.product_tmpl_id.name_lang:
                    thron_message += 'No-Name,'
            if not t.product_tmpl_id.technical_description:
                    thron_message += 'No-IT-Des,'
            if not t.product_tmpl_id.plating_description:
                    thron_message += 'No-EN-Des,'
            for v in t.shopify_product_ids:
                if not v.shopify_image_ids:
                    thron_message += 'No-IMGS,'
            t.thron_message = thron_message
    
    def clean_get_thron_image(self):
        for t in self:
            t.shopify_image_ids.unlink()
            for v in t.shopify_product_ids:
                v.product_id.ept_image_ids.unlink()
                v.product_id.get_thron_image()
    
    def get_thron_image(self):
        for t in self:
            for v in t.shopify_product_ids:
                v.product_id._cron_sync_get_content(domain=[('id','in',v.product_id.ids)])
        
    def get_thron_content(self):
        for t in self:
            for v in t.shopify_product_ids:
                v.product_id._cron_sync_get_products(product_ids=v.product_id)
        
    
    
    def generate_tags(self):
        for a in self:
            a.tag_ids= [(5,0,0)]
            tags = []
            tag_category = a.product_tmpl_id.categ_id.megacategory.lower() if a.product_tmpl_id.categ_id.megacategory else ''
            sequence = 0
            if tag_category:
                tags += [(0,0,{
                          'name':"category_%s" % (tag_category),
                          'sequence':sequence
                          })]
                sequence +=1
            variants = [variant for variant in a.product_tmpl_id.product_variant_ids]               
            stones = set()
            for v in variants:
                for s in v.stone_ids:
                    stones.add(s.id)
            
            for sid in stones:
                s = self.env['product.stone'].browse(sid)
                if s.stone_type_id:
                    tags += [(0,0,{
                              'name':"stone_%s" % (s.stone_type_id.name.lower() if s.stone_type_id.name else ''),
                              'sequence':sequence
                              })]
                    sequence +=1
                if s.megacolor_id:
                    tags += [(0,0,{
                              'name':"megacolor_%s" %(s.megacolor_id.name.lower() if s.megacolor_id.name else ''),
                              'sequence':sequence
                              })]
                    sequence +=1
            tag_collection = a.product_tmpl_id.collection_id.name.lower() if a.product_tmpl_id.collection_id.name else ''
            if tag_collection:
                tags += [(0,0,{
                          'name':"collection_%s" % (tag_collection),
                          'sequence':sequence
                          })] 
                sequence +=1
            features = a.product_tmpl_id.feature_ids
            for feature in features:
                if feature.for_shopify:
                    tags += [(0,0,{
                          'name':feature.name,
                          'sequence':sequence
                          })] 
                    sequence +=1
            a.tag_ids= tags
            
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    ept_financial_order_status = fields.Selection([('invoiced','Invoiced in Shopify'),('payed','Payed in Shopify')],copy=False,help="For Shopify Connector, do not create invoice but set order as payed")
    
    def shopify_set_pricelist(self, instance, order_response):
        pricelist = instance.shopify_pricelist_id if instance.shopify_pricelist_id else False
        return pricelist
    
#     def validate_and_paid_invoices_ept(self, work_flow_process_record):
#         """
#         This method will create invoices, validate it and paid it, according
#         to the configuration in workflow sets in quotation.
#         :param work_flow_process_record:
#         :return: It will return boolean.
#         """
#         self.ensure_one()
#         if work_flow_process_record.create_invoice:
#             self.ept_financial_order_status = 'invoiced'
#             if work_flow_process_record.register_payment:
#                 self.ept_financial_order_status = 'payed'
#         return True
    
    @api.constrains('shopify_instance_id')
    def _shopify_source(self):
        for a in self:
            if a.shopify_instance_id:
                shopify_source_id = self.env['utm.source'].search([('name','=',a.shopify_instance_id.name)],limit=1)
                if not shopify_source_id:
                    shopify_source_id = self.env['utm.source'].create({'name':a.shopify_instance_id.name})
                a.write({
                            'source_id':shopify_source_id.id,
                            'origin':a.shopify_order_id
                             })
                    
class ShopifyInstanceEpt(models.Model):
    _inherit = "shopify.instance.ept"
    
    lang = fields.Char('Lang for metafield',default="it")
    
class ShopifyProductProductEpt(models.Model):
    _inherit = "shopify.product.product.ept"
    
    def check_stock_type(self, instance, product_ids, prod_obj, warehouse):
        """
        This Method relocates check type of stock.
        :param instance: This arguments relocates instance of Shopify.
        :param product_ids: This argumentes product listing id of odoo.
        :param prod_obj: This argument relocates product object of common connector.
        :param warehouse:This arguments relocates warehouse of shopify export location.
        :return: This Method return prouct listing stock.
        """
        prouct_listing_stock = False
        if product_ids:
            if instance.shopify_stock_field.name == 'free_qty':
                prouct_listing_stock = prod_obj.get_free_qty(warehouse, product_ids)
            else:
                return super(ShopifyProductProductEpt,self).check_stock_type(instance,product_ids,prod_obj,warehouse)
        return prouct_listing_stock
    
    
    def shopify_set_template_value_in_shopify_obj(self, new_product, template, is_publish, is_set_basic_detail):
        res = super(ShopifyProductProductEpt,self).shopify_set_template_value_in_shopify_obj( new_product, template, is_publish, is_set_basic_detail)
        if is_set_basic_detail:
            instance = template.shopify_instance_id
            description = template.product_tmpl_id._get_meta_field('technical_description','it') if instance.lang == 'it' else template.product_tmpl_id._get_meta_field('plating_description','it')
            
            name = template.product_tmpl_id._get_meta_field('name_lang',instance.lang)
            if description:
                new_product.body_html = description  
            else:
                new_product.body_html = template.name
            if name:
                new_product.title = name  
            else:
                new_product.title = template.name
            
            new_product.metafields_global_title_tag=template.product_tmpl_id._get_meta_field('title',instance.lang) if template.product_tmpl_id._get_meta_field('title',instance.lang) else template.product_tmpl_id.name
            new_product.metafields_global_description_tag=template.product_tmpl_id._get_meta_field('meta_description',instance.lang)
        return res
                                 
    def shopify_prepare_variant_vals(self, instance, variant, is_set_price, is_set_basic_detail):
        variant_vals = super(ShopifyProductProductEpt,self).shopify_prepare_variant_vals(instance, variant, is_set_price, is_set_basic_detail)
        variant_vals.update({
                                 'grams': int(variant.product_id.weight_gr),
                                 'weight': (variant.product_id.weight_gr),
                                 'weight_unit': 'g'
                                 })
        return variant_vals