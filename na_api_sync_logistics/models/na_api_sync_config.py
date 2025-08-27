# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import json
import os
import gc
from odoo import fields, models, _, api
from odoo.exceptions import UserError
import xml.etree.ElementTree as ET
import requests
from xml.dom import minidom


class NaApiSyncConfig(models.Model):
    _inherit = 'na.api.sync.config'

    create_backorder = fields.Boolean(string='Create Backorder')

    def _cron_export_products(self):
        # a scheduled action was chosen for the export of products,
        # so that it can be scheduled when the system is not in use.
        sync_env = self.env['na.api.sync.env'].search([('api_type', '=', 'logistic')])
        product_config = sync_env.goods_registry
        if product_config:
            results = product_config.management_data_feed()

    def _cron_products_update(self):
        # gets the product quantity update configuration
        sync_env = self.env['na.api.sync.env'].search([('api_type', '=', 'logistic')])
        logistics_goods_inventory = sync_env.logistics_goods_inventory
        location = sync_env.location_id
        if logistics_goods_inventory and location:
            xml_dicts = logistics_goods_inventory.management_data_feed()
            for xml_dict in xml_dicts:
                values = logistics_goods_inventory.process_record(
                    xml_dict, logistics_goods_inventory.api_fields_ids, create_data=False)
                for line in values.get('line_ids'):
                    line[2].update({
                        'location_id': location.id,
                    })
                values.update({
                    'name': f"Battistolli - {logistics_goods_inventory.name}",
                    'location_ids': [(4, location.id)],
                    'product_ids': [(4, line[2]['product_id']) for line in values.get('line_ids') if line[2]['product_id']],
                    'line_ids': [line for line in values.get('line_ids') if line[2]['product_id']]
                })
                record = self.env[logistics_goods_inventory.model_id.model].create(values)
                # in this case we know that it is an inventor stock, so it is initiated and validated
                # TODO in the future will be to implement a better and more generic way
                record.action_start()
                record.action_validate()

    def _validate_picking_before_action_done(self, values):
        # Inherit to add custom functions
        return values

    @api.model
    def validate_picking(self, xml_dicts, create_backorder=False):
        # TODO Milor: add exceptions
        if xml_dicts:
            move_lines = self.api_fields_ids.filtered(
                lambda f: f.odoo_field_id.name == 'move_lines')
            if len(move_lines) > 1:
                move_lines = move_lines[0]
            if move_lines:
                move_lines_config = move_lines.field_config_id
                if move_lines_config:
                    lines_key = move_lines.ext_system_field
                    line_id_key = move_lines_config.api_fields_ids.filtered(
                        lambda l: l.odoo_field_id.name == 'id')
                    if len(line_id_key) > 1:
                        line_id_key = line_id_key[0]
                    qty_key = move_lines_config.api_fields_ids.filtered(
                        lambda l: l.odoo_field_id.name == 'quantity_done')
                    if len(qty_key) > 1:
                        qty_key = qty_key[0]
                    line_id_key = line_id_key.ext_system_field
                    qty_key = qty_key.ext_system_field
                    if line_id_key and qty_key:
                        pickings = self.env['stock.picking']
                        values = []
                        for xml_dict in xml_dicts:
                            lines = xml_dict.get(lines_key, [])
                            if type(lines) != list:
                                lines = [lines]
                            for line in lines:
                                line_id = int(line.get(line_id_key, 0))
                                move = self.env['stock.move'].search([('id', '=', line_id), ('state', 'not in', ['done', 'cancel'])])
                                if move:
                                    quantity = line.get(qty_key, '0000')
                                    if '.' not in quantity:
                                        quantity = f"{quantity[:-3]}.{quantity[-3:]}"
                                    quantity = float(quantity)
                                    move.quantity_done = quantity
                                    if move.picking_id not in pickings:
                                        pickings += move.picking_id
                                    values.append({'xml_dict': xml_dict, 'move': move,
                                                   'picking': move.picking_id})
                        self._validate_picking_before_action_done(values)
                        if pickings:
                            pickings.with_context(cancel_backorder=not create_backorder,
                                                  block_feed=True).action_done()

    def _cron_import_ftp_feed(self):
        # a scheduled action was chosen for the export of products,
        # so that it can be scheduled when the system is not in use.
        sync_env = self.env['na.api.sync.env'].search(
            [('api_type', '=', 'logistic')])
        logistics_goods_validation = sync_env.logistics_goods_validation
        logistics_goods_confirmation = sync_env.logistics_goods_confirmation
        if logistics_goods_validation:
            xml_dicts = logistics_goods_validation.management_data_feed()
            logistics_goods_validation.validate_picking(
                xml_dicts, sync_env.forecast_create_backorder)
        if logistics_goods_confirmation:
            xml_dicts = logistics_goods_confirmation.management_data_feed()
            logistics_goods_confirmation.validate_picking(
                xml_dicts, sync_env.delivery_create_backorder)
