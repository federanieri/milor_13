# -*- coding: utf-8 -*-
import logging
import json
import base64
import os
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# FIELDS_MAPPING = {
#     'keywords': 'keywords',
#     'meta-title': 'title',
#     'meta-descrizione': 'meta_description',
#     'descrizione-pietra': 'stone_description',
#     'descrizione-placcatura': 'plating_description',
#     'descrizione-collezione': 'collection_description',
#     'descrizione-lunga': 'general_description',
#     'quando-utilizzarlo': 'when_use',
#     'descrizione-tecnica-usata': 'technical_description',
#     'bullet-point': 'bullet_points'
# }

# probably use ISO code?
LANG_MAPPING = {
    'en_US': 'en',
    'it_IT': 'it',
    'fr_FR': 'fr'
}

EQUIVALENT_FIELDS_VARIANT = {
    'codice_sku':'93551',
    'barcode':'127511',
    'prezzo':'93552',
    'prezzo2':'116418',
    'prezzo1':'116417',
    'immagine_da_articolo_base':'93553',
    # 'image':'93554',
    'fotografia':'93555',
    'altra_variante':'93556',
    'size':'93561',
    'pietra':'93562',
    'placcatura':'99056',
    'metallo':'120469',
    'titolo_metallo':'120470',
    'testfile':'103223',
    'peso':'136988'
}

class ProductProduct(models.Model):
    # Private Attributes
    _inherit = 'product.product'

    # ------------------
    # Field Declarations
    # ------------------

    onpage_variant_id = fields.Char(string="OnPage Product ID")
    json_product_onpage = fields.Text(string="Json Product Onpage")
    
    # --------------
    # Helper Methods
    # --------------


    def create_image_attachment(self):
        for a in self:
            if not a.product_variant_image_ids and a.image_1920:
                attachment = a.env['ir.attachment'].search([('name','ilike',a.default_code or 'Image_'+str(a.id)),('mimetype','ilike','image/jpeg'),('res_id','=',a.id)], limit=1)
                if not attachment:
                    image = a.env['ir.attachment'].create(dict(
                        name=str(a.default_code) or 'Image_'+str(a.id),
                        datas=a.image_1920,
                        mimetype='image/jpeg',
                        res_model='product.product', 
                        res_id=a.id,
                        public=True,
                    ))
                    a._cr.commit()
                    """
                        Commit is required: OnPage is trying to take the url of an image that is not already existing
                        in DB as the transaction haven't finished.
                    """
            for image in a.product_variant_image_ids:
                attachment_id = a.env['ir.attachment'].sudo().search([('res_model','=','product.image'),('res_id','=',image.id),('index_content','=','image'),('res_field','=','image_1920')], limit=1)
                if attachment_id:
                    attachment_id.public = True
                    attachment_id._cr.commit()
                    """
                        Commit is required: OnPage is trying to take the non public attachment but the changes of public True aren't applied
                        until commit happens. 
                    """
    
    def _prepare_product_get_data(self, product_id):
        return {
            'resource_id': 7341,
            'fields': ['+'],
            'filter': ['_id', '=', product_id],
            'return': 'first'
        }
        
    def order_variant_images(self, domain=False):
        image_list = []

        if self.product_variant_image_ids:
            """
                At first time sort the list
            """
            sorted_list = sorted(self.product_variant_image_ids, key=lambda x: x.name.split('_')[-1])
            num_list = ['1','3','2']
            sorted_zipped_lists = sorted(zip(num_list,sorted_list))
            images = [element for _, element in sorted_zipped_lists] 
            for image in images:
                if image.ept_image_id:
                    image_list.append([image, image.ept_image_id.url])
                else:
                    attachment_id = self.env['ir.attachment'].sudo().search([('res_model','=','product.image'),('res_id','=',image.id),('index_content','=','image'),('res_field','=','image_1920')], limit=1)
                    _logger.info("ATTACHMENT ID :: %s" % attachment_id)
                    if attachment_id:
                        image_list.append([image, domain+ "/web/image?model=ir.attachment&field=datas&id=%s" % str(attachment_id.id)])
        return image_list


    def _prepare_product_post_data(self, domain=False):
        other_variant = ""
        stone_names = []
        size = ""
        plating = ""
        stone = []
        attachment_id = ""
        if self.product_template_attribute_value_ids:
            for line in self.product_template_attribute_value_ids:
                if line.name.lower() in ['altro', 'other']:
                    other_variant = line.name
        for attr in self.product_template_attribute_value_ids:
            if attr.attribute_id.unique_code_identifier == "STONE" or attr.attribute_id.name == "STONE":
                stone_names = [attr.product_attribute_value_id.name]
            if attr.attribute_id.unique_code_identifier == "SIZE" or attr.attribute_id.name.upper() in ["SIZE","TAGLIA"]:
                size = attr.product_attribute_value_id.name
            if attr.attribute_id.unique_code_identifier == "PLATING" or attr.attribute_id.name == "PLATING":
                plating = attr.product_attribute_value_id.name
                
        if self.plating_id:
            plating = self.plating_id.name
        elif self.metal_id:
            plating = self.metal_id.name
            
        if not stone_names and self.stone_ids:
            stone_names = [stone.name for stone in self.stone_ids]
        
        if not self.product_variant_image_ids.filtered(lambda r: r.ept_image_id) and self.image_1920:
            attachment = self.env['ir.attachment'].search([('name','ilike',self.default_code),('mimetype','ilike','image/jpeg'),('res_id','=',self.id)], limit=1)
            if attachment:
                attachment_id = attachment.id
        if self.env.context.get('just_images', None):
            data = {
                "resource_id": 7341,
                "translate": 1,
                "fields": {
                    "image": [{"name": a[0].display_name, "file": a[1]} for a in self.order_variant_images(domain)] or \
                            [{"name": self.default_code, "file": domain+ "/web/image?model=ir.attachment&field=datas&id=%s" % str(attachment_id)}], 
                },
                "relations": {
                    "prodotti": [self.product_tmpl_id.onpage_id if self.product_tmpl_id.onpage_id else None]
                }
            }
        else:
            data = {
                "resource_id": 7341,
                "translate": 1,
                "fields": {
                    "codice_sku": [{"value": self.default_code if self.default_code else ""}],
                    "prezzo": [{"value": self.price7 if self.price7 else 0}],
                    "prezzo1": [{"value": self.price8 if self.price8 else 0}],
                    "prezzo2": [{"value": self.price2 if self.price2 else 0}],
                    "image": [{"name": a[0].display_name, "file": a[1]} for a in self.order_variant_images(domain)] or \
                            [{"name": self.default_code, "file": domain+ "/web/image?model=ir.attachment&field=datas&id=%s" % str(attachment_id)}], 
                    "altra_variante": [{"value": other_variant}],
                    "size": [{"value":  size}],
                    "pietra": [{"lang": "it", "value": a} for a in stone_names],
                    "placcatura": [{"lang": "it", "value": plating}],
                    "metallo": [{"lang": "it", "value": self.metal_id.name if bool(self.metal_id) else ''}],
                    "titolo_metallo": [{"value": self.metal_title if bool(self.metal_title) else ''}],
                    "barcode": [{"value": self.barcode}],
                    "peso": [{"value": self.weight_gr}]
                },
                "relations": {
                    "prodotti": [self.product_tmpl_id.onpage_id if self.product_tmpl_id.onpage_id else None]
                }
            }
        if self.onpage_variant_id:
            data["id"] = self.onpage_variant_id
        return data

    def get_onpage_image(self, response=False, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        if self.onpage_variant_id:
            if not response:
                response = onpage_account.sync_to_odoo(self._prepare_product_get_data(self.onpage_variant_id))
            if response.get('image'):
                url = "No old url provided"
                res = response.get('fields')[EQUIVALENT_FIELDS_VARIANT.get('image')]
                _logger.info("RESPONSE :: %s" % json.dumps(res, indent=4, sort_keys=True))
                _logger.info("RES IMAGES LEN :: %s" % len(res))
                _logger.info("EPT IMAGES LEN :: %s" % len(self.ept_image_ids))
                _logger.info("EPT IMAGES :: {}".format(self.ept_image_ids))
                
                """
                    Remove images if they have been removed from OnPage
                """
                if len(res) < len(self.ept_image_ids):
                    self.ept_image_ids.unlink()
                
                for i in range(len(res)):
                    if i < len(self.ept_image_ids):
                        if res[i]['value']['token'] in [image.image_token for image in self.ept_image_ids]:
                            pass
                        elif res[i]['value']['token'] != self.ept_image_ids[i].image_token:
                            self.ept_image_ids[i].write({
                                    'url': onpage_account.get_image_querynator(res[i]['value']['token']) + ('.'+(response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')][i].get('value').get('ext') or 'png')),
                                    'old_url': url,
                                    'name': self.ept_image_ids[i].name,
                                    'image_token': res[i]['value']['token']
                                })
                    else:
                        onpage_account.create_image({
                            'template_id':self.product_tmpl_id.id,
                            'product_id': self.id,
                            'url': onpage_account.get_image_querynator(res[i]['value']['token']) + ('.'+(response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')][i].get('value').get('ext') or 'png')),
                            'name': res[i]['value']['name'],
                            'old_url': url,
                            'image_token': res[i]['value']['token']
                        })
                    

    def get_onpage_metacontent(self, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        self.write({
            'json_product_onpage': onpage_account.sync_to_odoo(self._prepare_product_get_data()).json()
        })

    def post_products(self, automatic=False, onpage_account=False, product_id=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            if product_id:
                products = self.search([('is_onpage_product', '=', True),('product_id', '=', product_id),('onpage_variant_id', '=', False)])
            else:
                products = self.search([('is_onpage_product', '=', True),('onpage_variant_id', '=', False)])

            for product in products:
                data = product._prepare_product_post_data()
                response = onpage_account.sync(data)
                if response.get('error_message'):
                    raise ValidationError(response.get('error_message'))
                if response.get('id'):
                    product.write({
                        'onpage_variant_id': response['id'],
                    })
                    product._cr.commit()
                    """
                        A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
                    """
                if response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')]:
                    for image in product.ept_image_ids:
                        image.write({
                                'url':response.get('token'),
                                'old_url': data['image'],
                                'image_token':response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')][i].get('value').get('token')
                            })

    def post_single_product(self, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        data = self._prepare_product_post_data(onpage_account.into_domain)
        response = onpage_account.sync(data)
        if response.get('error_message'):
            raise ValidationError(response.get('error_message'))
        if response.get('id'):
            self.write({
                'onpage_variant_id': response['id'],
            })
            self._cr.commit()
            """
                A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
            """
        # variants_images = self.order_variant_images(onpage_account.into_domain)
        # if variants_images and response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')]:
        #     for i, image in enumerate(variants_images):
        #         if image[0].ept_image_id:
        #             image[0].ept_image_id.write({
        #                     'url':onpage_account.get_image_querynator(response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')][i].get('value').get('token')) + '.png',
        #                     'old_url':data['fields']['image'][i].get('file'),
        #                     'image_token':response['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')][i].get('value').get('token')
        #                 })


    @api.model
    def _cron__sync_get_products(self, automatic=False, onpage_account=False, product_ids=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        products = onpage_account.list_products()
        for product in products:
            data = product.get_onpage_content()
            self.create(self.parse_to_model(data))

class ProductImage(models.Model):
    _inherit = "common.product.image.ept"

    image_token = fields.Char("Image OnPage Token", default="No token provided", readonly=True)
    old_url = fields.Char("Thron Url")
    
    @api.model 
    def write(self, vals):
        res = super(ProductImage, self).write(vals)
        return res
        
    def unlink(self):
        return super(ProductImage, self).unlink()

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    unique_code_identifier = fields.Char("Identifier")
    
class irAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def create(self, vals):
        res = super(irAttachment, self).create(vals)
        return res

