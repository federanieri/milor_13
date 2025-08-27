# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime
from PIL import Image
import requests
from io import BytesIO

from odoo import api, fields, models, registry, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, image_to_base64

_logger = logging.getLogger(__name__)

PEPPERI_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'pepperi.mixin']

    image_url = fields.Char(string="Image URL", help="Update the image from the URL on pepperi to image field",compute='_get_image',readonly=True)

    def _get_image(self):
        # for a in self:
        #     cimage = self.env['common.product.image.ept'].search([('default','=',True),('product_id','=',a.id),('url','!=',False)],limit=1)
        #     if not cimage:
        #         cimage = self.env['common.product.image.ept'].search([('default','=',True),('template_id','=',a.product_tmpl_id.id),('url','!=',False)],limit=1)
        #     a.image_url = cimage.url
        for a in self:
            cimage = self.env['common.product.image.ept'].search([('product_id','=',a.id),('url','!=',False)],limit=1)
            if not cimage:
                cimage = self.env['common.product.image.ept'].search([('template_id','=',a.product_tmpl_id.id),('url','!=',False)],limit=1)
            a.image_url = cimage.url
            
        
    def _pepperi_fields(self):
        return ['default_code', 'name', 'standard_price', 'lst_price', 'categ_id', 'description', 'to_pepperi', 'image_url']

    def open_image_from_url(self, image_url):
        try:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            return image_to_base64(image, image.format)
        except Exception as e:
            _logger.info(str(e))
            _logger.info(str(image_url))
            return False

    def _prepare_products_data(self, pepperi_items):
        for item in pepperi_items:
            product_data = self._prepare_product_data(item)
            yield product_data

    def _prepare_product_data(self, item):
        ProductCategory = self.env['common.product.brand.ept']
#         image_url = 'URL' in item.get('Image') and item['Image']['URL']
#         image = image_url and self.open_image_from_url(image_url) or False
        categ_id = ProductCategory.search([('name', '=', item.get('MainCategoryID', 'pepperi'))], limit=1)
        ModificationDateTime = datetime.datetime.strptime(item.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
        if not categ_id:
            categ_id = ProductCategory.create({'name': item.get('MainCategoryID', 'pepperi')})
        return {
            'name': item.get('Name', '') if item.get('Name', '') != '' else str(item.get('ExternalID','')),
            'default_code': item.get('ExternalID', ''),
            'standard_price': item.get('CostPrice', ''),
            'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'lst_price': item.get('Price', '1'),
            #'barcode': item.get('InternalID', ''),
            'product_brand_id': item.get('MainCategoryID') and categ_id and categ_id.id,
            'description': item.get('LongDescription'),
            'modification_datetime': item.get('ModificationDateTime'),
            'from_pepperi': True,
            'to_pepperi':True,
            'type': 'product',
#             'image_1920': image,
        }

    def _get_item_params(self):
        product = self.env['product.product'].search([('from_pepperi', '=', True), ('last_update_from_pepperi', '!=', False)], limit=1, order="last_update_from_pepperi desc")
        params = {
            # 'page': 1,
            'page_size': 10,
            'order_by': 'InternalID,ModificationDateTime'
        }
        if product.modification_datetime:
            params.update({
                'where': "ModificationDateTime>'%s'" % product.modification_datetime,
            })
        return params

    def _create_or_write_products(self, items):
        # we can use when we will use callback URL on pepperi
        ProductProduct = self.env['product.product']
        for item in items:
            product = ProductProduct.search([('default_code', '=', item['default_code'])], limit=1)
            if product:
                product.write(item)
            else:
                product = ProductProduct.create(item)
            ProductProduct |= product
        return ProductProduct

    @api.model
    def _cron_sync_pepperi_products(self, automatic=False, pepperi_account=False):
        items = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))

            params = self._get_item_params()
            pepperi_items = self._get_pepperi_items(pepperi_account, params=params, data={})
            items = self._prepare_products_data(pepperi_items)
            # TODO: create multiple records at once? create_multi?
            # self._create_or_write_products(items)
            ProductProduct = self.env['product.product']
            for item in items:
                product = ProductProduct.search([('default_code', '=', item['default_code'])], limit=1)
                if product:
                    del item['type']
                    product.write(item)
                else:
                    product = ProductProduct.create(item)
                if automatic:
                    self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            _logger.info('products synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : products synchronization issues."), level="info", path="/items", func="_cron_sync_pepperi_products")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True
    
    
        
    
        
    @api.model
    def _get_plating_and_stone_from_dict(self,p):
        res = ""
        if p.get('plating_id',False):
            res = p.get('plating_id')[1]
        if p.get('stone_ids',False):
            if res:
                res = res + "/"
            stone_dict = [self.env['product.stone'].browse(n).name for n in p.get('stone_ids')]
            stone_string = ""
            for s in stone_dict:
                if stone_string:
                    stone_string = stone_string + "+"
                stone_string = stone_string + s
            res = res + stone_string
        if not res:
            return ''
        else:
            return res
    
    @api.model
    def _get_product_template_code_from_dict(self,p):
        parent_code =  self.env['product.template'].browse(p.get('product_tmpl_id')[0]).default_code
        return parent_code if parent_code else ''
    
    @api.model
    def _get_parent_from_dict(self,p):
        return self.env['product.template'].browse(p.get('product_tmpl_id')[0]).default_code
        
    def _get_attribute_values_from_dict(self,p):
        product = self.env['product.product'].browse(p.get('id'))
        res = []
        for p in product.product_template_attribute_value_ids:
            res.append(p.name)
        if len(res)==0:
            res.append(product.default_code)
        if len(res)==1:
            if product.dimension:
                res.append(product.dimension)
        if len(res)==1:
            if product.size:
                res.append(product.size) 
        if len(res)==1:
            if product.weight_gr:
                res.append(product.weight_gr) 
        if len(res)==1:
            res.append(product.default_code)
        
        return res
            
    @api.model    
    def _prepare_product_data_for_pepperi(self, product_data,template_data):
        template_lines = [
                        [
                p.get('name'),                                                  #"Name",
                p.get('default_code'),                                              #ExternalID
                p.get('standard_price'),                                        #CostPrice
                p.get('lst_price'),                                             # Price
                p.get('product_brand_id')[1] if p.get('product_brand_id') else '', #MainCategoriId
                '',                                                         # Dimension1Code
                '',                                                         # Dimension1 Name
                '',                                                         #Dimension2Code
                '',                                                         # Dimensione2Name
                p.get('product_brand_id')[1] if p.get('product_brand_id') else '', #MainCategory
                p.get('name'),                                               #LongDescription
                'TRUE' if p.get('out_of_collection') else 'FALSE',               #Prop1
                'TRUE' if p.get('out_of_collection') else 'FALSE',              #Prop2
                '',                                                             #Prop3
                p.get('season_id')[1] if p.get('season_id') else '',         #Prop4
                '',                                                         #Prop5
                p.get('show_id')[1] if p.get('show_id') else '', #Prop6
                p.get('season_id')[1] if p.get('season_id') else '',        #Prop7
                p.get('collection_id')[1] if p.get('collection_id') else '', #Prop8
                self.env['product.category'].browse(p.get('categ_id')[0]).name if p.get('categ_id') else '',           #Prop9
                p.get('uom_id')[1] if p.get('uom_id') else '',                      #TSAClass                                                          #TSAClass
#                   p.get('metal_id')[1] if p.get('metal_id') else '',         # TSAmetal
                '',                                                           #TSAColorSize
                 p.get('metal_id')[1] if p.get('metal_id') else '',           #TSAMaterial
                 '',                                                        #TSAweight
                 '',                                                        #UPC
                ''                                                          #PArentExternalID
                ] for p in template_data
                        ]
        product_lines = [[
                p.get('name') if p.get('name') else '',                     #"Name",
                p.get('default_code') if p.get('default_code') else '',     #ExternalID
                p.get('standard_price'),                                    #CostPrice
                p.get('lst_price'),                                         # Price
                p.get('product_brand_id')[1] if p.get('product_brand_id') else "",  #MainCategoriId
                self._get_attribute_values_from_dict(p)[0],                           # Dimension1Code
                self._get_attribute_values_from_dict(p)[0],                           # Dimension1 Name
                self._get_attribute_values_from_dict(p)[1],                             #Dimension2Code
                self._get_attribute_values_from_dict(p)[1],                             # Dimensione2Name
                p.get('product_brand_id')[1] if p.get('product_brand_id') else '',  #MainCategory
                p.get('name'),                      #LongDescription
                'TRUE' if p.get('out_of_collection_variant') else 'FALSE',          #Prop1
                 p.get('length_cm').replace(".",",") if p.get('length_cm') else '',          #Prop2
                p.get('size') if p.get('size') else '',                             #Prop3
                p.get('season_id')[1] if p.get('season_id') else '',                #Prop4
                self._get_product_template_code_from_dict(p),                       #Prop5
                p.get('show_id')[1] if p.get('show_id') else '',        #Prop6
                p.get('season_id')[1] if p.get('season_id') else '',                #Prop7
                p.get('collection_id')[1] if p.get('collection_id') else '',        #Prop8
                self.env['product.category'].browse(p.get('categ_id')[0]).name if p.get('categ_id') else '',                  #Prop9
                p.get('uom_id')[1] if p.get('uom_id') else '',                      #TSAClass                                                          
#                   p.get('metal_id')[1] if p.get('metal_id') else '',                 #TSAmetal    
                p.get('milor_extension_code') if p.get('milor_extension_code') else '',     #TSAColorSize
                  p.get('metal_id')[1] if p.get('metal_id') else '',                  #TSAMaterial
                 ("%5.1f" % p.get('weight_gr')).replace(".",","),                                         #TSAweight    
                p.get('barcode') if p.get('barcode') else '',                       #UPC
                self._get_parent_from_dict(p)                                       #PArentExternalID
                ] for p in product_data]
        data = {
            "Headers": [
                "Name",
                "ExternalID",
                "CostPrice", 
                "Price", 
                "MainCategoryID",
                "Dimension1Code",
                "Dimension1Name",
                "Dimension2Code",
                "Dimension2Name",
                "MainCategory",
                "LongDescription",
                "Prop1",
                "Prop2",
                "Prop3",
                "Prop4",
                "Prop5",
                "Prop6",
                "Prop7",
                "Prop8",
                "Prop9",
                "TSAClass",
#                  "TSAMetal",
                 "TSAColorSize",
                 "TSAMaterial",
                 "TSAWeight",
                "UPC",
                "ParentExternalID" 
                
                
            ],
            "Lines": template_lines + product_lines 
        }
        return data

    def send_pepperi_products(self):
        self._cron_sync_post_pepperi_products(ids=self.ids)

    @api.model
    def _cron_sync_post_pepperi_products(self, automatic=False, pepperi_account=False,ids=False):
        items = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            if not ids:
                domain = [('to_pepperi', '=', True), ('default_code', '!=', False),('default_code', '!=', "")]
            else:
                domain = [('to_pepperi', '=', True), ('id', 'in', ids)]
            if pepperi_account and pepperi_account.last_product_synch_date and not ids:
                domain.append(('write_date','>=',pepperi_account.last_product_synch_date))
            _logger.info(domain)
            product_product = self.env['product.product'].search(domain)
            last_datetime = False
            if product_product:
                last_datetime = max(product.write_date for product in product_product)
                product_product_data = product_product.read(
                                                            ['default_code', 
                                                             'name', 
                                                             'standard_price',
                                                             'lst_price',
                                                             'categ_id',
                                                             'description',
                                                             'image_url',
                                                             'product_brand_id',
                                                             'metal_id',
                                                             'barcode',
                                                             'milor_extension_code',
                                                             'size',
                                                             'product_tmpl_id',
                                                             'season_id',
                                                             'collection_id',
                                                             'weight_gr',
                                                             'plating_id',
                                                             'stone_ids',
                                                             'out_of_collection_variant',
                                                             'uom_id',
                                                             'show_id',
                                                             'length_cm',
                                                             'dimension',
                                                             'id'
                                                             ])
                product_template = self.env['product.template']
                for p in product_product :
                    if p.product_tmpl_id.product_variant_count>1 and p.product_tmpl_id.default_code :
                        product_template |= p.product_tmpl_id
                product_template_data = product_template.read(
                                                            ['default_code', 
                                                             'name', 
                                                             'standard_price',
                                                             'lst_price',
                                                             'categ_id',
                                                             'description',
                                                             'product_brand_id',
                                                             'metal_id',
                                                             'season_id',
                                                             'collection_id',
                                                             'out_of_collection',
                                                             'uom_id',
                                                             'show_id',
                                                             'id'
                                                             ])
                data = self._prepare_product_data_for_pepperi(product_product_data,product_template_data)
                _logger.info(data)
                items = self._post_pepperi_items(pepperi_account, params={}, data=data)
                if 'JobID' in items:
                    bulk_job_info = pepperi_account.get_data_by_uri(params={}, data={}, uri=items.get('URI', '/'))
                    ModificationDateTime = datetime.datetime.strptime(bulk_job_info.get('ModificationDate'), PEPPERI_DATETIME_TZ)
                    pepperi_account._log_message("bulk_job_info", str(bulk_job_info), level="info", path=str(items), func="_cron_sync_post_pepperi_products")
                    product_product.write({
                            'last_update_to_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        })
                if automatic:
                    self.env.cr.commit()
                self.env['common.product.image.ept']._cron_sync_post_pepperi_product_images(products=product_product)
            pepperi_account.last_product_synch_date = last_datetime if last_datetime else pepperi_account.last_product_synch_date
        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            _logger.info('products post synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : post products synchronization issues."), level="info", path="/bulk/items/json", func="_cron_sync_post_pepperi_products")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    def _prepare_inventory_data_for_pepperi(self, products_data):
        data = {
                "Headers": [
                    "InStockQuantity", "ItemExternalID"
                ],
                "Lines": []
            }
        data['Lines'] += [[product.get('free_qty'), product.get('default_code')] for product in products_data]
        return data


    def send_pepperi_stock(self):
        self._cron_sync_pepperi_stock(ids=self.ids)

    @api.model
    def _cron_sync_pepperi_stock(self, automatic=False, pepperi_account=False,ids=False):
        items = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            if ids:
                products = self.env['product.product'].search([('to_pepperi', '=', True),('id','in',ids)])
            else:
                products = self.env['product.product'].search([('to_pepperi', '=', True)])
            if products:
                products_data = products.read(['barcode', 'default_code', 'free_qty'])
                data = self._prepare_inventory_data_for_pepperi(products_data)
                _logger.info(data)
                items = self._post_pepperi_inventory(pepperi_account, params={}, data=data)
                if 'JobID' in items:
                    bulk_job_info = pepperi_account.get_data_by_uri(params={}, data={}, uri=items.get('URI', '/'))
                    pepperi_account._log_message("bulk_job_info", str(bulk_job_info), level="info", path=str(items), func="_cron_sync_pepperi_stock")

                templates = self.env['product.template']
                for p in products:
                    templates |= p.product_tmpl_id
                products_data = templates.read(['default_code', 'free_qty'])
                data = self._prepare_inventory_data_for_pepperi(products_data)
                _logger.info(data)
                items = self._post_pepperi_inventory(pepperi_account, params={}, data=data)
                if 'JobID' in items:
                        bulk_job_info = pepperi_account.get_data_by_uri(params={}, data={}, uri=items.get('URI', '/'))
                        pepperi_account._log_message("bulk_job_info", str(bulk_job_info), level="info", path=str(items), func="_cron_sync_pepperi_stock")
            if automatic:
                self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            _logger.info('Inventory synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : Post Inventory synchronization issues."), level="info", path="/bulk/inventory/json", func="_cron_sync_pepperi_stock")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    def _get_pepperi_items(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of items including details about each item (Products) and its nested objects.
            Ex:
                [
                    {
                        "InternalID": barcode,
                        "ExternalID": default_code,
                        "AllowDecimal": false,
                        "MainCategoryID": categ_id,
                        "CostPrice": standard_price,
                        "Image": {},
                        "LongDescription": description,
                        "MainCategory": categ_id,
                        "ModificationDateTime": "2020-05-06T19:27:11Z",
                        "Name": name,
                        "Price": lst_price,
                    }
                ]"""
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/items',
            params=params, data=data)
        return content

    def _post_pepperi_items(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of items including details about each item (Products) and its nested objects.
            Ex:
                [
                    {
                        "InternalID": barcode,
                        "ExternalID": default_code,
                        "AllowDecimal": false,
                        "MainCategoryID": categ_id,
                        "CostPrice": standard_price,
                        "Image": {},
                        "LongDescription": description,
                        "MainCategory": categ_id,
                        "ModificationDateTime": "2020-05-06T19:27:11Z",
                        "Name": name,
                        "Price": lst_price,
                    }
                ]"""
        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/bulk/items/json',
            params=params, data=data)
        return content

    def _post_pepperi_inventory(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of items including details about each item (Products) and its nested objects.
            Ex:
                data = {
                    "Headers": [
                        "InStockQuantity", "ItemInternalID"
                    ],
                    "Lines": [
                        [value, value],
                        [value, value]
                    ]
                }
        """
        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/bulk/inventory/json',
            params=params, data=data)
        return content
