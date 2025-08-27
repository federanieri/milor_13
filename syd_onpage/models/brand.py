# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, registry, _
from pyparsing import col
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductBrand(models.Model):
    # Private Attributes
    _inherit = 'common.product.brand.ept'

    # ------------------
    # Field Declarations
    # ------------------

    collection_ids = fields.One2many('product.collection', 'brand_id', string="Collections")
    onpage_id = fields.Char(string="Brand OnPage ID")
    is_onpage_brand = fields.Boolean(string="Is OnPageBrand")

    # --------------
    # Helper Methods
    # --------------

    def _prepare_brand_post_data(self, image_url=""):
        data = {
            "resource_id": 7335,
            "fields": {
                "nome": [{"value": self.name}],
                "descrizione": [{"value": self.description}],
            },
            # "relations": {
            #     "collezione": list(map(lambda x: x.onpage_id if x.onpage_id else None, self.collection_ids)),
            # }
        }
        if self.onpage_id:
            data["id"] = self.onpage_id
        return data

    def post_brands(self, onpage_account=False):
        """Sync everything using brand relationships"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            for brand in self.search([('is_onpage_brand', '=', True),('onpage_id', '=', False)]):
                data = brand._prepare_brand_post_data("")
                response = onpage_account.sync(data)
                if response.get('id'):
                    brand.write({
                        'onpage_id': response['id'],
                    })
                    brand._cr.commit()
                    """
                        A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
                    """

    def post_single_brand(self, onpage_account=False):
        """Sync everything using brand relationships"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            for brand in self.filtered(lambda b: b.is_onpage_brand and not b.onpage_id) or self.filtered(lambda b: b._context['new_brand'] if 'new_brand' in b._context else None):  # , ('onpage_id', '=', False)]):
                data = brand._prepare_brand_post_data("")
                response = onpage_account.sync(data)
                if response.get('error_message'):
                    raise ValidationError(response.get('error_message'))
                if response.get('id'):
                    brand.write({
                        'onpage_id': response['id'],
                    })
                    brand._cr.commit()
                    """
                        A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
                    """
