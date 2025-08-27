# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime

from odoo import api, fields, models, registry, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

PEPPERI_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"


class Pricelist(models.Model):
    _name = 'product.pricelist'
    _inherit = ['product.pricelist', 'pepperi.mixin']

    pepperi_internal_id = fields.Integer('InternalID', default=0)
    pepperi_name = fields.Char('Pepperi Name for Import Sale Order')
    
    def _pepperi_fields(self):
        return ['name', 'currency_id', 'to_pepperi']

    def _prepare_pricelists_data_from_pepperi(self, pepperi_items):
        pricelist_data = []
        if not pepperi_items:
            return pricelist_data
        ResCurrency = self.env['res.currency']
        for item in pepperi_items:
            ModificationDateTime = datetime.datetime.strptime(item.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
            currency = ResCurrency.search([('name', '=', item.get('CurrencySymbol', ''))], limit=1)
            pricelist_data.append({
                'name': item.get('ExternalID', ''),
                'currency_id': currency and currency.id or self.env.company.currency_id.id,
                'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'pepperi_internal_id': item.get('InternalID', ''),
                'modification_datetime': item.get('ModificationDateTime'),
                'from_pepperi': True
            })
        return pricelist_data

    def _prepare_pricelists_data(self, pepperi_items):
        pricelist_data = []
        if not pepperi_items:
            return pricelist_data
        for item in pepperi_items:
            ModificationDateTime = datetime.datetime.strptime(item.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
            pricelist_data.append({
                'name': item.get('ExternalID', ''),
                'last_update_to_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'pepperi_internal_id': item.get('InternalID'),
                'modification_datetime': item.get('ModificationDateTime'),
                'need_synch_to_pepperi': False
            })
        return pricelist_data

    def _prepare_pricelist_data_for_pepperi(self, pricelist_data):
        data = {
            "Headers": [
                "InternalID", "ExternalID", "Hidden", "Description", "CurrencySymbol"
            ],
            "Lines": [
                [p.get('pepperi_internal_id', 0), p.get('name'), False, p.get('name'), p.get('currency_id')[1]] for p in pricelist_data
            ]
        }
        return data

    def _get_item_params(self):
        params = dict(
            page=1,
            page_size=100,
        )
        return params

    def _create_or_write_pricelist(self, items):
        # we can user when we will use callback URL on pepperi
        ProductPricelist = self.env['product.pricelist']
        for item in items:
            pricelist = ProductPricelist.search([('name', '=', item.pop('name'))], limit=1)
            if pricelist:
                pricelist.write(item)
            else:
                pricelist = ProductPricelist.create(item)
            ProductPricelist |= pricelist
        return ProductPricelist

    @api.model
    def _cron_sync_pepperi_pricelist(self, automatic=False, pepperi_account=False):
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
            product_pricelist = self.env['product.pricelist'].search([('to_pepperi', '=', True)])
            if product_pricelist:
                pricelist_data = product_pricelist.read()
                data = self._prepare_pricelist_data_for_pepperi(pricelist_data)
                items = self._post_pepperi_price_lists(pepperi_account, params={}, data=data)
                if 'JobID' in items:
                    bulk_job_info = pepperi_account.get_data_by_uri(params={}, data={}, uri=items.get('URI', '/'))
                    pepperi_account._log_message("bulk_job_info", str(bulk_job_info), level="info", path=str(items), func="_cron_sync_pepperi_pricelist")
                    params = self._get_item_params()
                    params.update({
                        'where': "ExternalID IN (%s)" % ','.join("'{0}'".format(d['name']) for d in pricelist_data)
                    })
                    pepperi_pricelist_items = self._get_pepperi_price_lists(pepperi_account, params=params, data={})
                    p_pl_data = self._prepare_pricelists_data(pepperi_pricelist_items)
                    self._create_or_write_pricelist(p_pl_data)
                    if automatic:
                        self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            _logger.info('Pricelist synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : Pricelist synchronization issues."), level="info", path="/bulk/price_lists/json", func="_cron_sync_pepperi_pricelist")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    def _get_pepperi_price_lists(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of price_lists including details about each price list and its nested objects.
            return =  {
                    "InternalID": 0,
                    "ExternalID": "test_pricelist",
                    "Hidden": false,
                    "Description": "test price list",
                    "CurrencySymbol": "USD"
                }
        """
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/price_lists',
            params=params, data=data)
        return content

    def _post_pepperi_price_lists(self, pepperi_account, params={}, data={}):
        """
            Upserts (updates/inserts) a single price list data. ExternalID is required in case of insert
            and either InternalID or ExternalID are required in case of update
            data = {
                "Headers": [
                    "InternalID", "ExternalID", "Hidden", "Description", "CurrencySymbol"
                ],
                "Lines": [
                    ["InternalID_value", "ExternalID_value", "Hidden_valu", "Description_value", "CurrencySymbol_value"]
                ]
            }
        """
        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/bulk/price_lists/json',
            params=params, data=data)
        return content


class PricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'pepperi.mixin']

    def _pepperi_fields(self):
        return ['applied_on', 'pricelist_id', 'to_pepperi', 'product_tmpl_id', 'categ_id', 'product_id', 'currency_id', 'compute_price', 'fixed_price']

    def _prepare_pricelist_item_data_for_pepperi(self, product_pricelist_item):
        data = {
            "Headers": ["PriceListExternalID", "ItemExternalID", "Price", "Hidden"],
            "Lines": []
        }
        products = self.env['product.product']
        for item in product_pricelist_item:
            if item.applied_on == '3_global':
                products |= products.search([('to_pepperi', '=', True)])
            if item.applied_on == '2_product_category':
                products |= products.search([('categ_id', 'child_of', item.categ_id.id),('to_pepperi', '=', True)])
            if item.applied_on == '1_product':
                products |= item.product_tmpl_id.product_variant_ids
            if item.applied_on == '0_product_variant':
                products |= item.product_id
            for p in products:
                price_get = item.pricelist_id.price_get(p.id, item.min_quantity)
                data["Lines"] += [[item.pricelist_id.pepperi_name, p.default_code, price_get.get(item.pricelist_id.id, 0.0), False]]
        return data

    @api.model
    def _cron_sync_pepperi_pricelist_item(self, automatic=False, pepperi_account=False,pricelist_id=False):
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

            applied_on = ['3_global','0_product_variant', '1_product', '2_product_category']
            if pricelist_id:
                product_pricelist_item = self.env['product.pricelist.item'].search([('applied_on', 'in', applied_on),('pricelist_id', '=', pricelist_id.id),('pricelist_id.to_pepperi', '=', True)])
            else:
                product_pricelist_item = self.env['product.pricelist.item'].search([('applied_on', 'in', applied_on),('pricelist_id.to_pepperi', '=', True)])
            if product_pricelist_item:
                data = self._prepare_pricelist_item_data_for_pepperi(product_pricelist_item)
                items = self._post_pepperi_pricelist_item_prices(pepperi_account, params={}, data=data)
                if 'JobID' in items:
                    bulk_job_info = pepperi_account.get_data_by_uri(params={}, data={}, uri=items.get('URI', '/'))
                    ModificationDateTime = datetime.datetime.strptime(bulk_job_info.get('ModificationDate'), PEPPERI_DATETIME_TZ)
                    pepperi_account._log_message("bulk_job_info", str(bulk_job_info), level="info", path=str(items), func="_cron_sync_pepperi_pricelist_item")
                    product_pricelist_item.write({
                            'last_update_to_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        })
            if automatic:
                self.env.cr.commit()
        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            _logger.info('Pricelist Item synchronization response from pepperi ::: {}'.format(items))
            pepperi_account._log_message(str(e), _("Pepperi : Pricelist Item synchronization issues."), level="info", path="/bulk/item_prices/json", func="_cron_sync_pepperi_pricelist_item")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    def _get_pepperi_pricelist_item_prices(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of item prices including details about each item price and its nested objects.
            return =  [
                        {
                            "CreationDateTime": "2020-05-12T09:28:39Z",
                            "Hidden": false,
                            "ModificationDateTime": "2020-05-12T09:28:39Z",
                            "Price": 100,
                            "Item": {
                              "Data": {
                                "InternalID": 57616333, => product's barcode
                                "UUID": "cc8ccab8-d6bc-49c4-a2b6-c0f00e73c89a",
                                "ExternalID": "WSBZ01569.RQ-L" => product's default_code
                              },
                              "URI": "/items/57616333"
                            },
                            "PriceList": {
                              "Data": {
                                "InternalID": 1851079,
                                "UUID": "22347ece-9cef-4546-9d15-39edd3c77f3d",
                                "ExternalID": "PTNEW" PriceList's name
                              },
                              "URI": "/price_lists/1851079"
                            }
                          },
                    ]
        """
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/item_prices',
            params=params, data=data)
        return content

    def _post_pepperi_pricelist_item_prices(self, pepperi_account, params={}, data={}):
        """
            Upserts (updates/inserts) a single item price data. In order to DELETE an item price Set the Hidden field to true.
            data = {
                    "Headers": [
                        "PriceListExternalID", "ItemExternalID", "Price", "Hidden"
                        ],
                    "Lines": [
                                ["PriceListExternalID_value", "ItemExternalID_value", 120, false],
                        ]
                    }
        """
        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/bulk/item_prices/json',
            params=params, data=data)
        return content
