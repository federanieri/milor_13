# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models
import base64
import requests


class NaApiSyncEnv(models.Model):
    _inherit = 'na.api.sync.env'

    api_type = fields.Selection(selection_add=[('logistic', 'Logistics Integration - FTP')])
    forecast_goods = fields.Many2one('na.api.sync.config', string='Forecast Goods')
    logistics_goods_validation = fields.Many2one('na.api.sync.config',
                                                 string='Logistics Goods Validation')
    forecast_create_backorder = fields.Boolean(string='Forecast Create Backorder')

    goods_delivery = fields.Many2one('na.api.sync.config', string='Goods Delivery')
    logistics_goods_confirmation = fields.Many2one('na.api.sync.config',
                                                   string='Logistics Goods Confirmation')
    delivery_create_backorder = fields.Boolean(string='Delivery Create Backorder')

    goods_registry = fields.Many2one('na.api.sync.config', string='Goods Registry')
    logistics_goods_inventory = fields.Many2one(
        'na.api.sync.config', string='Logistics Goods Inventory')
    location_id = fields.Many2one(
        'stock.location', string='Location', check_company=True,
        domain="[('usage', 'in', ['internal', 'transit'])]",
        help="Through this configuration you can define in which warehouse "
             "the received quantities will be corrected.")
