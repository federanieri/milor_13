# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime
from PIL import Image
import requests
from io import BytesIO

from odoo import api, fields, models, registry, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, image_to_base64

_logger = logging.getLogger(__name__)

PEPPERI_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"


class ProductImage(models.Model):
    _inherit = 'common.product.image.ept'
    
    to_pepperi = fields.Boolean('To Pepperi',related="product_id.to_pepperi",store=True,default=False)
    
    @api.model
    def _cron_sync_post_pepperi_product_images(self, automatic=False, pepperi_account=False,products=False):
        if not products:
            products = self.env['product.product']
        items = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            domain = [('to_pepperi', '=', True), ('default', '=',True), ('product_id', 'in',products.ids)]
            if pepperi_account and pepperi_account.last_product_synch_date:
                domain.append(('write_date','>=',pepperi_account.last_product_synch_date))
            product_product = self.env['common.product.image.ept'].search(domain)
            last_datetime = False
            for p in product_product:
                data = self._prepare_product_image_for_pepperi(p.product_id)
                items = self._post_pepperi_items(pepperi_account, params={}, data=data) 
            self.env.cr.commit()
            
        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            _logger.info('products post synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : post products image synchronization issues."), level="info", path="/items/", func="_cron_sync_post_pepperi_product_images")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    def _prepare_product_image_for_pepperi(self, product):
        data = {
                'ExternalID':product.default_code,
                'Image':{
                    'URL':product.image_url,
                    'MimeType':'image/jpg',
                    'FileName':'image.jpg'
                    }
                }
        return data

   

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    

    def _post_pepperi_items(self, pepperi_account, params={}, data={}):
        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/items',
            params=params, data=data)
        return content

    