# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.stock_barcode.controllers.main import StockBarcodeController

import json

import logging
_logger = logging.getLogger(__name__)


class OdAS2(http.Controller):
    @http.route('/odas2', type='http', methods=['POST'], auth='public', csrf=False, cors='*')
    def odas2(self, access_token, op_code, sender_id, receiver_id, message_id, data, **post):
        OdAS2MessageQueue = request.env['odas2.message.queue'].sudo()

        # INFO: parses data as a json format.
        jdata = json.loads(data)

        res_messages, res_status = OdAS2MessageQueue.process_message_from_data(
            access_token,
            op_code,
            sender_id,
            receiver_id,
            jdata,
            request.httprequest.host
        )
        if res_status != 200:
            vals = {
                'message_id': message_id,
                'access_token': access_token,
                'op_code': op_code,
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'data': json.dumps(jdata, indent=4),
                'response_status': res_status,
                'response_message': res_messages
            }
            # INFO: checks by message_id if it already exists...
            message = OdAS2MessageQueue.search([('message_id', '=', message_id)], limit=1)
            # INFO: then creates or update according to that.
            if not message:
                OdAS2MessageQueue.create(vals)
            else:
                message.write(vals)

        return http.Response(res_messages, status=res_status)


class StockBarcodeControllerExt(StockBarcodeController):

    def try_open_picking(self, barcode):
        """ If barcode represents a picking, open it
        """

        so = request.env['sale.order'].search([
            ('commercehub_co', '=', barcode),
        ], limit=1)
        if so:
            po = request.env['purchase.order'].search([
                ('origin', 'ilike', so.name),
            ], limit=1)
            for corresponding_picking in po.total_picking_ids.filtered(lambda x : x.state == 'assigned').sorted(key=lambda r: r.picking_type_sequence):
                    return self.get_action(corresponding_picking.id)
            for corresponding_picking in po.total_picking_ids.filtered(lambda x : x.state == 'waiting').sorted(key=lambda r: r.picking_type_sequence):
                    return self.get_action(corresponding_picking.id)
            for corresponding_picking in so.total_picking_ids.filtered(lambda x : x.state == 'assigned').sorted(key=lambda r: r.picking_type_sequence):
                    return self.get_action(corresponding_picking.id)
            for corresponding_picking in so.total_picking_ids.filtered(lambda x : x.state == 'waiting').sorted(key=lambda r: r.picking_type_sequence):
                    return self.get_action(corresponding_picking.id)
        return super(StockBarcodeControllerExt, self).try_open_picking(barcode)
