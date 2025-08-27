# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, registry, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    # Private Attributes
    _inherit = 'product.category'

    # ------------------
    # Field Declarations
    # ------------------

    is_onpage_category = fields.Boolean(string="Is OnPage Category")
    onpage_id = fields.Char(string="Category OnPage ID")
    product_ids = fields.One2many('product.template', 'categ_id', string="Products")

    # --------------
    # Helper Methods
    # --------------

    def _prepare_category_post_data(self, image_url=""):
        data = {
                "resource_id": 13333,
                "fields": {
                    "nome":  [{"lang": "it", "value": self.name if bool(self.name) else ""}],
                },
            }
        if self.onpage_id:
            data["id"] = self.onpage_id
        return data

    def post_categories(self, onpage_account=False):
        """Sync all of the Odoo categories to OnPage"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        else:
            for category in self.search([('is_onpage_category', '=', True),('onpage_id', '=', False)]):
                data = category._prepare_category_post_data("")
                response = onpage_account.sync(data)
                if response.get('id'):
                    category.write({
                        'onpage_id': response['id'],
                    })
                    category._cr.commit()
                    """
                        A commit is required: If Onpage submits a category but an error occurs later, that ID would not be in Odoo but the category would be in onpage.
                    """
                for product in category.product_ids:
                    if product.is_onpage_product:
                        data = product.prepare_product_template_post_data()
                        response = onpage_account.sync(data)
                        if response.get('id') and not product.onpage_id:
                            product.write({
                                'onpage_id': response['id'],
                            })
                            product._cr.commit()
                            """
                                A commit is required: If Onpage submits a product but an error occurs later, that ID would not be in Odoo but the product would be in onpage.
                            """

    def post_single_category(self, onpage_account=False):
        """Sync a single category to OnPage"""
        if not onpage_account:
            onpage_account = self.env['onpage.account'].search([], limit=1)
        if not onpage_account:
            _logger.info('No OnPage Account Found')
            return True
        data = self._prepare_category_post_data()
        response = onpage_account.sync(data)
        if response.get('error_message'):
            raise ValidationError(response.get('error_message'))
        if response.get('id'):
            self.write({
                'onpage_id': response['id'],
            })
            self._cr.commit()
            """
                A commit is required: If Onpage submits a category but an error occurs later, that ID would not be in Odoo but the category would be in onpage.
            """
