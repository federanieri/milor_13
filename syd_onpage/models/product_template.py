# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, registry, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

FIELDS_MAPPING = {
    'keywords': 'keywords',
    'meta-title': 'title',
    'meta-descrizione': 'meta_description',
    'descrizione-pietra': 'stone_description',
    'descrizione-placcatura': 'plating_description',
    'descrizione-collezione': 'collection_description',
    'descrizione-lunga': 'general_description',
    'quando-utilizzarlo': 'when_use',
    'descrizione-tecnica-usata': 'technical_description',
    'bullet-point': 'bullet_points'
}

# probably use ISO code?
LANG_MAPPING = {
    'en_US': 'en',
    'it_IT': 'it',
    'fr_FR': 'fr'
}

KNOW_ERROR_CODES = {
    400: _('Bad Request! The request is malformed, such as if the body does not parse or some validation fails or '
           'semantically incorrect.'),
    401: _('Unauthorized ! Authentication is required and has failed or has not yet been provided.'),
    403: _(
        'Forbidden! The server is refusing action. The user might not have the necessary permissions for a resource.'),
    412: _('Invalid input. No active recipients found.'),
    450: _('Token is expired!'),
    500: _('Internal Server Error ! An internal error occurred in OnPage. Please contact to OnPage APi Team.')
}

class ProductTemplate(models.Model):
    # Private Attributes
    _inherit = 'product.template'

    # ------------------
    # Field Declarations
    # ------------------
    seo_description = fields.Char(string="SEO Description")
    is_onpage_product = fields.Boolean(string='Is OnPage Product')
    onpage_id = fields.Char(string="OnPage Product ID")
    json_template_onpage = fields.Text(string="Json Template Onpage")

    # --------------
    # Helper Methods
    # --------------

    @api.onchange('product_brand_id')
    def set_product_brand_id(self):
        """
        Set automatically the brand of the product in collection
        """
        if bool(self.product_brand_id):
            self.collection_id.brand_id = self.product_brand_id

    @api.constrains('is_onpage_product')
    def _check_onpage_product(self):
        """
        Cannot set is_onpage_product to True instead you have collection and brand set
        """
        if self.is_onpage_product:
            self.with_context(from_template=True).check_products_requirements()
            
    def check_products_requirements(self):
        self.ensure_one()
        
        if bool('from_template' in self._context) and bool(self._context.get('from_template')):
            if not bool(self.collection_id):
                raise ValidationError(_('This product cannot be upload in OnPage because: The COLLECTION is NOT set for this product.'))   
            elif not bool(self.collection_id.brand_id):
                if bool(self.product_brand_id):
                    self.collection_id.brand_id = self.product_brand_id
                else:
                    raise ValidationError(_('This product cannot be upload in OnPage because: The collection selected has NO BRAND SET'))

    def prepare_product_template_post_data(self):
        """ Return error if there is not collezione or brand set in product template"""
        
        self.check_products_requirements()

        if not bool(self.collection_id.brand_id.onpage_id) or self.onpage_id:
            if bool(self.collection_id.brand_id):
                self.collection_id.brand_id.is_onpage_brand = True
                self.collection_id.brand_id.post_single_brand() 
        if not self.collection_id.onpage_id or self.onpage_id:
            self.collection_id.is_onpage_collection = True
            self.collection_id.post_single_collection()
        if not self.categ_id.onpage_id or self.onpage_id:
            self.categ_id.is_onpage_category = True
            self.categ_id.post_single_category()
        
        if self.env.context.get('update_info', None):
            data = {
                "resource_id": 7338,
                "fields": {
                    "nome": [
                        {"lang": "it", "value": self.name},
                    ],
                    "bullet_point":[
                        {"lang":k, 'value':v} for k,v in eval(self.bullet_points).items()] if self.bullet_points else [{"lang": "it", "value":""} 
                    ],
                    "descrizione_seo": [
                        {"lang": "it", "value": "Descrizione SEO"},
                        {"lang": "en", "value": "SEO Description"}
                    ],
                    "tag": [
                        {"value": a.name} for a in self.tag_product_ids
                    ],
                },
                "relations": {
                    "collezione": [self.collection_id.onpage_id if self.collection_id.onpage_id else None],
                    "categorie": [self.categ_id.onpage_id if self.categ_id.onpage_id else None],
                }
            }
        else:
            data = {
                "resource_id": 7338,
                "fields": {
                    "nome": [
                        {"lang": "it", "value": self.name},
                    ],
                    "codice_padre": [{"lang": "it", "value": self.default_code if self.default_code else ""}],
    #                 "descrizione": 
    #                     [{"lang":k, 'value':v} for k,v in eval(self.description_lang).items()] if self.description_lang else "", 
                    "bullet_point":[
                        {"lang":k, 'value':v} for k,v in eval(self.bullet_points).items()] if self.bullet_points else [{"lang": "it", "value":""} 
                    ],
                    "genere": [
                        {"lang": "it", "value": self.genre_id.name if self.genre_id.name else ""},
                    ],
                    "misura": [
                        {"value": self.size if self.size else ""}
                    ],
                    "stagione": [
                        {"value": self.season_id.name if self.season_id else ""}
                    ],
                    "descrizione_seo": [
                        {"lang": "it", "value": "Descrizione SEO"},
                        {"lang": "en", "value": "SEO Description"}
                    ],
                    "tag": [
                        {"value": a.name} for a in self.tag_product_ids
                    ],
                },
                "relations": {
                    "collezione": [self.collection_id.onpage_id if self.collection_id.onpage_id else None],
                    "categorie": [self.categ_id.onpage_id if self.categ_id.onpage_id else None],
                }
            }
        if self.onpage_id:
            data["id"] = self.onpage_id
        return data

    def post_products_template(self, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            for product_to_send in self.search([('is_onpage_product', '=', True),('onpage_id', '=', False)]):
                _logger.info("Product to send: %s " % product_to_send)
                data = product_to_send.prepare_product_template_post_data()
                _logger.info("Data to send: %s" % data)
                _logger.info("Variants data to send: %s" % self.product_variant_ids)
                response = onpage_account.sync(data)
                if not product_to_send.onpage_id and response.get('id'):
                    product_to_send.write({
                        'onpage_id': response['id'],
                    })
                    product_to_send._cr.commit()
                    """
                        A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
                    """
                    if len(self.product_variant_ids) > 0 and not self.env.context.get('update_info', None):
                        for i in self.product_variant_ids:
                            i.post_single_product()

    def post_single_product_template(self, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        data = self.with_context(from_template=True).prepare_product_template_post_data()
        response = onpage_account.sync(data)
        if response.get('error_message'):
            raise ValidationError(response.get('error_message'))
        if response.get('id'):
            self.write({
                'onpage_id': response['id'],
            })
            self._cr.commit()
            """
                A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
            """
        if len(self.product_variant_ids) > 0 and not self.env.context.get('update_info', None):
            for i in self.product_variant_ids:
                i.post_single_product()

    def get_onpage_metacontent(self, onpage_account=False):
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        data = {
            'resource_id': 7338,
            'id': self.onpage_id,
            'fields': ['+']
        }
        self.write({
            'json_template_onpage': onpage_account.sync_to_odoo(data).json()
        })

    def post_products_template(self):
        errors = []
        notification = {}
        for r in self:
            try:
                r.post_single_product_template()
            except Exception as e:
                if len(self) > 1:
                    if e.name in KNOW_ERROR_CODES.values():
                        raise e
                    else:
                        errors.append(r.default_code or r.display_name)
                        pass
                else:
                    raise e
        if errors:        
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('WARNING'),
                                'message': "The products %s couldn't be uploaded to OnPage, as NOT COLLECTION or BRAND is configured." % (', '.join([str(e) for e in errors])),
                                'type':'danger',
                                'sticky': True }
                            }
        else:
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('INFORMATION'),
                                'message': "All selected products have been successfully uploaded into OnPage!",
                                'type':'success',
                                'sticky': False }
                            }
        return notification
    
    def post_images(self):
        errors = []
        notification = {}
        message_error = ''
        for r in self:
            try:
                if not r.onpage_id:
                    message_error = 'This product template is not on Onpage!'
                    raise ValidationError(_(message_error))
                for i in r.product_variant_ids:
                    i.with_context(just_images=True).post_single_product()

            except Exception as e:
                if len(self) > 1:
                    if e.name in KNOW_ERROR_CODES.values():
                        raise e
                    else:
                        errors.append(r.default_code or r.display_name)
                        pass
                else:
                    raise e
        if errors or message_error:        
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('WARNING'),
                                'message': message_error or "The products %s couldn't be uploaded to OnPage, as NOT COLLECTION or BRAND is configured." % (', '.join([str(e) for e in errors])),
                                'type':'danger',
                                'sticky': True }
                            }
        else:
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('INFORMATION'),
                                'message': "All selected products have been successfully uploaded into OnPage!",
                                'type':'success',
                                'sticky': False }
                            }
        return notification

    def update_data_info(self):
        errors = []
        notification = {}
        message_error = ''
        for r in self:
            try:
                if not r.onpage_id:
                    message_error = 'This product template is not on Onpage!'
                    raise ValidationError(_(message_error))
                r.with_context(update_info=True).post_products_template()

            except Exception as e:
                if len(self) > 1:
                    if e.name in KNOW_ERROR_CODES.values():
                        raise e
                    else:
                        errors.append(r.default_code or r.display_name)
                        pass
                else:
                    raise e
        if errors or message_error:        
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('WARNING'),
                                'message': message_error or "The products %s couldn't be uploaded to OnPage, as NOT COLLECTION or BRAND is configured." % (', '.join([str(e) for e in errors])),
                                'type':'danger',
                                'sticky': True }
                            }
        else:
            notification = {'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': ('INFORMATION'),
                                'message': "All selected products have been successfully uploaded into OnPage!",
                                'type':'success',
                                'sticky': False }
                            }
        return notification
