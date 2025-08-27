import base64
import logging

from odoo import models, fields

import json

_logger = logging.getLogger(__name__)


class ImportJsonFileWizard(models.TransientModel):
    _name = "sale.order.import.json.wizard"
    _description = 'Sale Order Import Json Wizard'

    json_file = fields.Binary('File', required=True)

    def import_json_file(self):
        OdAS2MessageQueue = self.env['odas2.message.queue'].sudo()

        json_file = base64.decodebytes(self.json_file)

        recs = json.loads(json_file)

        for rec in recs:

            res_messages, res_status = OdAS2MessageQueue.process_message_from_data(
                rec['access_token'],
                rec['op_code'],
                rec['sender_id'],
                rec['receiver_id'],
                json.loads(rec['data']),
            )

        _logger.info("Completed")
        return True
