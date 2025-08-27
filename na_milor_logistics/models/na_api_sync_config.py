# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models


class NaApiSyncConfig(models.Model):
    _inherit = 'na.api.sync.config'

    def _validate_picking_before_action_done(self, values):
        values = super()._validate_picking_before_action_done(values)
        sync_env = self.env['na.api.sync.env'].search(
            [('api_type', '=', 'logistic')])
        logistics_goods_validation = sync_env.logistics_goods_validation
        logistics_goods_confirmation = sync_env.logistics_goods_confirmation
        if logistics_goods_validation and logistics_goods_validation == self:
            for value in values:
                xml_dict = value.get('xml_dict', {})
                picking = value.get('picking', self.env['stock.picking'])
                rlt_numbolla = xml_dict.get('RLT_NUMBOLLA', '')
                rlt_dtbolla = xml_dict.get('RLT_DTBOLLA', '')
                if rlt_numbolla or rlt_dtbolla:
                    picking.write({
                        'vendor_number_ddt': rlt_numbolla,
                        'vendor_date_ddt': rlt_dtbolla,
                    })
        elif logistics_goods_confirmation and logistics_goods_confirmation == self:
            for value in values:
                xml_dict = value.get('xml_dict', {})
                picking = value.get('picking', self.env['stock.picking'])
                tracking_number = xml_dict.get('TrackingNumber', '')
                if tracking_number:
                    picking.write({
                        'carrier_tracking_ref': tracking_number,
                    })

        return values
