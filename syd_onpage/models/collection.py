# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, registry, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductCollection(models.Model):
    # Private Attributes
    _inherit = 'product.collection'

    # ------------------
    # Field Declarations
    # ------------------

    is_onpage_collection = fields.Boolean(string="Is OnPage Collection")
    onpage_id = fields.Char(string="Collection OnPage ID")
    brand_id = fields.Many2one('common.product.brand.ept', string="Brand")
    product_ids = fields.One2many('product.template', 'collection_id', string="Products")
    description = fields.Text(string="Description")
    website_description = fields.Text(string="Website Description")

    # --------------
    # Helper Methods
    # --------------

    def _prepare_collection_post_data(self, image_url=""):
        data = {
                "resource_id": 7336,
                "fields": {
                    "nome": [{"value": self.name if self.name else ""}],
                    "descrizione": [{"lang": "it", "value": self.description if self.description else ""}],
                    "descrizione_sito": [{"lang": "it", "value": self.website_description if self.website_description else ""}],
                },
                "relations": {
                    "brands": [self.brand_id.onpage_id if self.brand_id.onpage_id else None],
                    # "prodotti": list(map(lambda x: x.onpage_id if x.onpage_id else None, self.product_ids)),
                }
            }
        if self.onpage_id:
            data["id"] = self.onpage_id
        return data

    def post_collections(self, onpage_account=False):
        """Sync all of the collection to OnPage"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            for collection in self.search(['|',('is_onpage_collection', '=', True),('onpage_id', '=', True)]):
                data = collection._prepare_collection_post_data("")
                response = onpage_account.sync(data)
                if response.get('id'):
                    collection.write({
                        'onpage_id': response['id'],
                    })
                    collection._cr.commit()
                    """
                        A commit is required: If Onpage submits a collection but an error occurs later, that ID would not be in Odoo but the collection would be in onpage.
                    """

    def post_single_collection(self, onpage_account=False):
        """Sync a single collection to OnPage"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        data = self._prepare_collection_post_data("")
        response = onpage_account.sync(data)
        if response.get('error_message'):
            raise ValidationError(response.get('error_message'))
        if response.get('id'):
            self.write({
                'onpage_id': response['id'],
            })
            self._cr.commit()
            """
                A commit is required: If Onpage submits a collection but an error occurs later, that ID would not be in Odoo but the collection would be in onpage.
            """
        if not bool(list(response.get('rel_ids').values())[0]):
            self.brand_id.is_onpage_brand = True
            self.brand_id.with_context(new_brand=True).post_single_brand()
            data = self._prepare_collection_post_data("")
            response = onpage_account.sync(data)
