# -*- coding: utf-8 -*-

import json
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

"""
    OnPage Response Code
    When OnPage receives a request to an API endpoint, a number of different HTTP status codes can be returned
    in the response depending on the original request.
"""

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

EQUIVALENT_FIELDS_BRAND = {
    'nome':'93522',
    'imagine':'93523',
    'descrizione':'93524',
    'marchio':'93527'
}

EQUIVALENT_FIELDS_COLLEZIONE = {
    'nome':'93528',
    'immagine':'93529',
    'descrizione':'93530',
    'descrizione_sito':'93531'
}

EQUIVALENT_FIELDS_PRODUCT = {
    'nome':'93535',
    'codice_padre':'99057',
    'descrizione':'93536',
    'bullet_point':'116416',
    'misura':'103505',
    'stagione':'127512',
    'genere':'93540',
    'descrizione_seo':'93544',
    'tag_title':'121768',
    'tag': '136992'
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

EQUIVALENT_FIELDS_COLORE = {
    'nome':'93545',
    'image':'93546'
}

EQUIVALENT_FIELDS_CATEGORIE = {
    'nome':'93534'
}


class OnPageAccount(models.Model):
    # Private Attributes
    _name = 'onpage.account'
    _description = 'OnPage Account'

    # ------------------
    # Fields Declaration
    # ------------------

    # {7335: 'Brands', 7336: 'Collezione', 7337: 'Categorie', 7338: 'Prodotti', 7339: 'Colore', 7341: 'Variante'}
    company_id = fields.Many2one('res.company', string="Company account", default=lambda self: self.env.company)
    name = fields.Char(string='Account Name', required=True)
    onpage_api_token = fields.Char(string='OnPage Api Token', required=True)
    onpage_api_url = fields.Char(string='OnPage Api Url', required=True)
    onpage_images_api = fields.Char(string='OnPage Api Url', required=True)
    last_synch_date = fields.Datetime(string='Last Synch Date')
    last_product_update_date = fields.Datetime(string='Last Product Update Date')
    into_domain = fields.Char(string="Domain", default="https://milor.odoo.com")

    # --------------
    # Action Methods
    # --------------

    def action_open_onpage_product(self):
        self.ensure_one()
        action_data = self.env.ref('syd_onpage.action_onpage_products').read()[0]
        return action_data

    def action_perform_sync_brand_with_onpage(self):
        brands = self.env['common.product.brand.ept'].search([('is_onpage_brand', '=', True),('onpage_id', '=', False)])
        for brand in brands:
            brand.post_single_brand()
        self.action_perform_get_brands()

    def action_perform_sync_collections_with_onpage(self):
        collections = self.env['product.collection'].search([('is_onpage_collection', '=', True),('onpage_id', '=', False)])
        for collection in collections:
            collection.post_single_collection()
        self.action_perform_get_collections()

    def action_perform_sync_categories_with_onpage(self):
        categories = self.env['product.category'].search([('is_onpage_category', '=', True),('onpage_id', '=', False)])
        for category in categories:
            category.post_categories()
        self.action_perform_get_categories()

    def action_perform_sync_products_with_onpage(self):
        product = self.env['product.template']
        product.post_products_template()
        self.action_perform_get_product_template()

    def action_perform_sync_variants_with_onpage(self):
        variant = self.env['product.product']
        variant.post_products()
        self.action_perform_get_product_product()
        
    def action_perform_sync_with_onpage(self):
        self.action_perform_sync_brand_with_onpage()
        self.action_perform_sync_collections_with_onpage()
        self.action_perform_sync_categories_with_onpage()
        self.action_perform_sync_products_with_onpage()
        self.action_perform_sync_variants_with_onpage()
        self.action_perform_get_products()
        return True

    def action_perform_get_products(self):
        brands = self.list_brands()
        collections = self.list_collections()
        categories = self.list_categories()
        products = self.list_products()
        variants = self.list_variants()
        for brand in brands:
            self.create_brand(brand)
        for collection in collections:
            self.create_collection(collection)
        for category in categories:
            self.create_category(category)
        for product in products:
            self.create_product(product)
        for variant in variants:
            self.create_variant(variant)
        return True
    
    def action_perform_get_product_template(self):
        products = self.list_products()
        for product in products:
            self.create_product(product)
        return True
    
    def action_perform_get_product_product(self):
        variants = self.list_variants()
        for variant in variants:
            self.create_variant(variant)
        return True

    def action_perform_get_brands(self):
        brands = self.list_brands()
        for brand in brands:
            self.create_brand(brand)
        return True
    
    def action_perform_get_collections(self):
        collections = self.list_collections()
        for collection in collections:
            self.create_collection(collection)
        return True
    
    def action_perform_get_categories(self):
        categories = self.list_categories()
        for category in categories:
            self.create_category(category)
        return True


    # -------------------
    # API Calling Methods
    # -------------------

    @api.model
    def get_account(self):
        return self.search([('company_id', '=', self.env.company.id)])

    def _get_project_informations(self):
        """This method return the onpage project schema json"""

        return requests.get('{}/{}/schema'.format(self.onpage_api_url, self.onpage_api_token)).json()

    def get_querynator(self):
        """This method return the GET API URL basing on API_URL and API_TOKEN"""

        return '{}/{}/query'.format(self.onpage_api_url, self.onpage_api_token)

    def get_image_querynator(self, img_token):
        """This method return the GET IMAGE API URL basing on API_URL and API_TOKEN"""

        return '{}/{}'.format(self.onpage_images_api, img_token)

    def _get_postinator(self):
        """This method return the POST API URL basing on API_URL and API_TOKEN"""

        return '{}/{}/things'.format(self.onpage_api_url, self.onpage_api_token)

    def _get_resources(self):
        """This method return a dictionary mapping labels to corresponding idsthe basing on the schema of the project"""

        return {i['label']: i['id'] for i in self._get_project_informations()['resources']}

    def _get_content_by_id(self, onpage_id, resource_id):
        return requests.get(self.get_querynator(), {
            'resource_id': resource_id, 'id': onpage_id, 'return': 'first'}).json()

    def list_brands(self):
        """ Returns a list of brands using _get_resources() method to establish which resource to use
        """
        return requests.get(self.get_querynator(),
                            {'resource_id': self._get_resources()['Brands'], 'fields': '+', 'return': 'list'}).json()

    def list_collections(self):
        """ Returns a list of collections using _get_resources() method to establish which resource to use
        """
        return requests.get(self.get_querynator(),
                            {'resource_id': self._get_resources()['Collezione'], 'fields': '+',
                             'return': 'list'}).json()

    def list_categories(self):
        """ Returns a list of collections using _get_resources() method to establish which resource to use
        """
        return requests.get(self.get_querynator(),
                            {'resource_id': self._get_resources()['Categorie'], 'fields': '+', 'return': 'list'}).json()

    def list_products(self):
        """ Returns a list of products using _get_resources() method to establish which resource to use
        """
        return requests.get(self.get_querynator(),
                            {'resource_id': self._get_resources()['Prodotti'], 'fields': '+', 'return': 'list'}).json()

    def list_variants(self):
        """ Returns a list of products using _get_resources() method to establish which resource to use
        """
        return requests.get(self.get_querynator(),
                            {'resource_id': self._get_resources()['Variante'], 'fields': '+', 'return': 'list'}).json()

    # -------------------
    # Syncing Methods
    # -------------------

    def _sync_with_onpage(self, http_method, data=None):
        self.ensure_one()
        data = data or {}
        response = {}
        message = ''
        if http_method == 'POST':
            service_url = self._get_postinator()
            try:
                resp = requests.post(service_url, json=data)
                _logger.info('response status code : '.format(resp.status_code))
                if resp.status_code != 200:
                    _logger.info('request url : {}'.format(service_url))
                    _logger.info('request data : {}'.format(data))

                if resp.status_code == 403:
                    data = {k: data[k] for k in data if k != 'id'}
                    resp = requests.post(service_url, json=data)
                elif resp.status_code in KNOW_ERROR_CODES:
                    message = KNOW_ERROR_CODES[resp.status_code]
                    message = message + '( {} )'.format(resp.json())
                    raise ValidationError(message)
                response = resp.json()
                _logger.info('response from OnPage ::: {}'.format(response))
            except requests.HTTPError as ex:
                _logger.error("%s" % (str(ex)), exc_info=True)
            except Exception as ex:
                _logger.error("%s" % (str(ex)), exc_info=True)
                message = message or 'Unexpected error ! please report this to your administrator.'
                response['error_message'] = _(message)
        else:
            service_url = self.get_querynator()
            try:
                resp = requests.get(service_url, json=data)
                _logger.info('request url : {}'.format(resp.url))
                resp.raise_for_status()
                response = resp.json()
                _logger.info('response from OnPage ::: {}'.format(response))
            except requests.HTTPError as ex:
                resp = requests.get(service_url, json=data)
                _logger.error("%s" % (str(ex)), exc_info=True)
                level = 'warning'
                if resp.text:
                    text = json.loads(resp.text)
                    message = text['message']
                elif resp.status_code in KNOW_ERROR_CODES:
                    message = KNOW_ERROR_CODES[resp.status_code]
                else:
                    message = _('Unexpected error ! please report this to your administrator.')
                response['error_message'] = message
            except Exception as ex:
                _logger.error("%s" % (str(ex)), exc_info=True)
                response['error_message'] = _('Unexpected error ! please report this to your administrator.')

        return response

    def sync(self, data):
        """Odoo to Onpage Sync"""
        return self._sync_with_onpage(
            http_method='POST',
            data=data,
        )

    def update_products(self, data):
        return self._sync_with_onpage(
            http_method='POST',
            data=data,
        )

    def sync_to_odoo(self, data):
        """Onpage to Odoo"""
        return self._sync_with_onpage(
            http_method='GET',
            data=data,
        )

    # -------------------
    # Creation Methods
    # -------------------

    def create_brand(self, json):
        brand = self.env["common.product.brand.ept"].search([('onpage_id', '=', json['id'])])
        
        nome = json['fields'][EQUIVALENT_FIELDS_BRAND.get('nome')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_BRAND.get('nome')]) else False
        descrizione = json['fields'][EQUIVALENT_FIELDS_BRAND.get('descrizione')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_BRAND.get('descrizione')]) else False

        if brand:
            brand.write({
                'name': nome,
                'description': descrizione,
                'onpage_id': json['id']})
        else:
            self.env["common.product.brand.ept"].create({
                'name': nome,
                'description': descrizione,
                'onpage_id': json['id']})

    def create_collection(self, json):
        collection = self.env["product.collection"].search([('onpage_id', '=', json['id'])])
        
        nome = json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('nome')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('nome')]) else False
        descrizione = json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('descrizione')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('descrizione')]) else False
        descrizione_sito = json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('descrizione_sito')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_COLLEZIONE.get('descrizione_sito')]) else False

        if collection:
            collection.write({
                'name': nome,
                'description': descrizione,
                'website_description': descrizione_sito,
                'onpage_id': json['id']})
        else:
            self.env["product.collection"].create({
                'name': nome,
                'description': descrizione,
                'website_description': descrizione_sito,
                'onpage_id': json['id']})

    def create_category(self, json):
        category = self.env["product.category"].search([('onpage_id', '=', json['id'])])
        
        nome = json['fields'][EQUIVALENT_FIELDS_CATEGORIE.get('nome')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_CATEGORIE.get('nome')]) else False
     
        if category:
            category.write({
                'name': nome,
                'onpage_id': json['id']})
        else:
            self.env["product.category"].create({
                'name': nome,
                'onpage_id': json['id']})

    def create_product(self, json):
        product = self.env["product.template"].search([('onpage_id', '=', json['id'])])
        
        nome = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('nome')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('nome')]) else False
        descrizione = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('descrizione')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('descrizione')]) else False
        codice_padre = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('codice_padre')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('codice_padre')]) else False
        genere = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('genere')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('genere')]) else False
        misura = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('misura')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('misura')]) else False
        descrizione_seo = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('descrizione_seo')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('descrizione_seo')]) else False
        bullet_point = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('bullet_point')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('bullet_point')]) else False
        stagione = json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('stagione')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_PRODUCT.get('stagione')]) else False

        collezione = json['relations'][EQUIVALENT_FIELDS_VARIANT.get('collezione')][0].get('value') if (bool(json['relations']) and bool(json['relations'][EQUIVALENT_FIELDS_VARIANT.get('collezione')])) else False


        if product:
            product.write({
                'name': nome,
                'description': descrizione,
                'milor_code': codice_padre,
                'genre_id': self.env['product.genre'].search([('name', 'ilike', genere)]),
                'size': misura,
                'seo_description': descrizione_seo,
                'bullet_points': bullet_point,
                'season_id': self.env['product.season'].search([('name', 'ilike', stagione)]),
                
                'collection_id': self.env['product.collection'].search([('name', 'ilike', collezione)]),
                'categ_id': json['relations']['categorie'],
                
                'onpage_id': json['id']})
        else:
            self.env["product.template"].create({
                'name': nome,
                'description': descrizione,
                'milor_code': codice_padre,
                'genre_id': self.env['product.genre'].search([('name', 'ilike', genere)]),
                'size': misura,
                'seo_description': descrizione_seo,
                'bullet_points': bullet_point,
                'season_id': self.env['product.season'].search([('name', 'ilike', stagione)]),
                
                'collection_id': self.env['product.collection'].search([('name', 'ilike', json['relations']['collezione'])]),
                'categ_id': json['relations']['categorie'],
                
                'onpage_id': json['id']})

    def create_image(self, json):
        image = self.env["common.product.image.ept"].create(json)

    def create_variant(self, json):
        variant = self.env["product.product"].search([('onpage_variant_id', '=', json['id'])])

        """
            Get values from the response of OnPage
        """
        
        codice_sku = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('codice_sku')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('codice_sku')]) else False
        prezzo = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo')]) else False
        prezzo1 = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo1')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo1')]) else False
        prezzo2 = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo2')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('prezzo2')]) else False
        images = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')] if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('image')]) else False
        altra_variante = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('altra_variante')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('altra_variante')]) else False
        size = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('size')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('size')]) else False
        pietra = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('pietra')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('pietra')]) else False
       
        placcatura = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('placcatura')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('placcatura')]) else False
        metallo = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('metallo')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('metallo')]) else False
        titolo_metallo = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('titolo_metallo')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('titolo_metallo')]) else False
        barcode = json['fields'][EQUIVALENT_FIELDS_VARIANT.get('barcode')][0].get('value') if bool(json['fields'][EQUIVALENT_FIELDS_VARIANT.get('barcode')]) else False
        prodotti = json['relations'][EQUIVALENT_FIELDS_VARIANT.get('prodotti')][0].get('value') if (bool(json['relations']) and bool(json['relations'][EQUIVALENT_FIELDS_VARIANT.get('prodotti')])) else False
        
#         if pietra and not pietra in self.product_template_attribute_value_ids:
#             attribute_id = self.env['product.attribute'].search([('name','ilike',"STONE")])
#         if size and not size in self.product_template_attribute_value_ids:
#             attribute_id = self.env['product.attribute'].search([('name','ilike',"TAGLIA")])
#         if altra_variante and not altra_variante in self.product_template_attribute_value_ids:
#             attribute_id = self.env['product.attribute'].search([('name','ilike',"PLATING")])

        
        if variant:
            if images:
                variant.get_onpage_image(json)  
                
            variant.write({
                'default_code': codice_sku,
                'price7': prezzo,
                'price8': prezzo1,
                'price2': prezzo2,
                # "immagine_da_articolo_base": [{"value": "IMMAGINE_DA_ARTICOLO_BASE"}],
                # "fotografia": [{"value": "FOTOGRAFIA"}],
#                 'product_template_attribute_value_ids': [
#                                                             (6, 0, product_template_attribute_values.ids)
#                                                         ],
                'size': size,
               # 'stone_name': pietra,
                'plating_id': self.env['product.plating'].search([('name', 'ilike', placcatura)]) if bool(placcatura) else False,
                'metal_id': self.env['product.metal'].search([('name', 'ilike', metallo)]) if bool(metallo) else False,
                'metal_title': titolo_metallo,
                'barcode': barcode,
                'onpage_variant_id': json['id']})
        else:
            product_tmpl_id = self.env['product.template'].search([('onpage_id','=',prodotti)]) if bool(prodotti) else False
            variant = self.env["product.product"].create({
                'default_code': codice_sku,
                'price7': prezzo,
                'price8': prezzo1,
                'price2': prezzo2,
                # "immagine_da_articolo_base": [{"value": "IMMAGINE_DA_ARTICOLO_BASE"}],
                # "fotografia": [{"value": "FOTOGRAFIA"}],
#                 'product_template_attribute_value_ids': [
#                                                             (6, 0, product_template_attribute_values.ids)
#                                                         ],
                'size': size,
               # 'stone_name': pietra,
                'plating_id': self.env['product.plating'].search([('name', 'ilike', placcatura)]) if bool(placcatura) else False,
                'metal_id': self.env['product.metal'].search([('name', 'ilike', metallo)]) if bool(metallo) else False,
                'metal_title': titolo_metallo,
                'barcode': barcode,
                'product_tmpl_id': product_tmpl_id,
                'onpage_variant_id': json['id']})
                    
            if images:
                variant.get_onpage_image()  
