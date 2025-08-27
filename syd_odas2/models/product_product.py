# -*- coding: utf-8 -*-

import datetime
import requests

from odoo import api, fields, models, registry, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ['product.product', 'odas2.mixin', 'odas2.streams.mixin']

    def _to_as2_fields(self):
        # return ['to_as2', 'qty_available']
        return []

    # INFO: cron job taking care of synching products marked to be updated to AS2.
    @api.model
    def _cron_odas2_sync_product_product(self, automatic=False):
        resp = None

        # TODO: need to evolve to_as2 and need_to_need_synch_to_as2 because we have to handle companies.
        #       So, these fields need to contain reference to all involved companies.
        #       to_as2 = fields.Many2many('res.company.sync'...
        #       need_synch_to_as2 = fields.Many2many('res.company.sync'...
        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))

            # ProductProduct = self.env['product.product'].sudo()
            # recs = ProductProduct.search([('need_synch_to_as2', '=', True)])
            stream_ids = self.env['odas2.stream'].search([])

            for stream_id in stream_ids:
                if stream_id.product_ids:
                    data = dict(
                        access_token=stream_id.company_id.odas2_access_token,
                        format='hubxml',
                        sender_id=stream_id.sender_id,
                        receiver_id=stream_id.receiver_id,
                        vendor_id=stream_id.vendor_id,
                        merchant_id=stream_id.merchant_id,
                        op_code='CREATE_PRODUCT',
                    )

                    data.update(stream_id.product_ids._prepare_dict_for_as2(stream_id))

                    if stream_id.company_id.odas2_url:
                        resp = requests.post(stream_id.company_id.odas2_url, json=data)
                        if resp.status_code == 200:
                            # INFO: updates as2 info of the products just sent to commercehub inventory.
                            stream_id.product_ids.write({
                                # 'need_synch_to_as2': False,
                                'last_update_to_as2': datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                            })
                        else:
                            _logger.info('Product creation synchronization response from OdAS2 server ::: {}'.format(resp.text))

                        if automatic:
                            self.env.cr.commit()
                    else:
                        _logger.info(f"No OdAS2 Url Found for stream {stream_id.name}")

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            if resp:
                _logger.info('Product creation synchronization response from OdAS2 server ::: {}'.format(resp.text))
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass

        return True

    def _prepare_dict_for_as2(self, stream):
        # INFO: only products with a valid commercehub_code are evaluated.
        return {'products': [{
                'vendor_SKU': rec.commercehub_code,
                'description': rec.name,
                # INFO: if stream force_qty is greater than -1 then force product qty to set value else get real one.
                'qtyonhand': stream.force_qty > -1 and str(stream.force_qty) or str(rec.free_qty),
                'available': 'YES' if rec.free_qty else 'NO',
                'unit_cost': str(rec.standard_price),
        } for rec in self if rec.commercehub_code ]}
