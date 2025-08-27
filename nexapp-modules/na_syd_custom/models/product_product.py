from odoo import api, exceptions, fields, models, _, SUPERUSER_ID, registry

import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    out_of_collection = fields.Boolean('Fuori Collezione', track_visibility='onchange')
    out_of_collection_variant = fields.Boolean('Fuori Collezione Estensione', track_visibility='onchange')
    supplies_last = fields.Boolean('Ad Esaurimento', track_visibility='onchange')
