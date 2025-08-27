# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import requests
import base64
from requests.auth import HTTPBasicAuth

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

"""
    Pepperi Response Code
    When Pepperi receives a request to an API endpoint, a number of different HTTP status codes can be returned
    in the response depending on the original request.
"""

KNOW_ERROR_CODES = {
    401: _('Unauthorized ! The necessary authentication credentials are not present in the request or are incorrect..'),
    400: _('Bad Request! The request was not understood by the server, generally due to bad syntax.'),
    404: _('Not Found ! The requested resource could not be found (incorrect or invalid URI).'),
    500: _('Internal Server Error ! An internal error occurred in Pepperi. Please contact our API support team : api@support.pepperi.com so that our support team could investigate it.'),
    429: _('Too Many Requests! The request was not accepted because the application has exceeded the rate limit. See the API Rate Limit documentation for a breakdown of Pepperi\'s rate-limiting mechanism.'),
    501: _('Not Implemented! The requested endpoint is not available on that particular resource, e.g: currently we do not support POST for the users resource.'),
    504: _('Gateway Timeout! The request could not complete in time. Try breaking it down with our support team.')
}


class PepperiAccount(models.Model):
    # Private Attributes
    _name = 'pepperi.account'
    _description = 'Pepperi Account'

    # ------------------
    # Fields Declaration
    # ------------------

    name = fields.Char(string='Account Name', required=True)
    pepperi_api_login = fields.Char(string='Pepperi Api Login', required=True)
    pepperi_api_password = fields.Char(string='Pepperi Api Password', required=True)
    pepperi_api_url = fields.Char(string='Pepperi Api url', required=True)
    pepperi_company_id = fields.Char(string='Pepperi Company ID')
    pepperi_consumer_key = fields.Char(string='Pepperi Consumer Key', required=True)
    pepperi_consumer_secret = fields.Char(string='Pepperi Consumer Secret', required=True)
    pepperi_api_version = fields.Selection(
        selection=[('v1.0', 'v1.0')],
        string='Pepperi API Version',
        required=True, default='v1.0')
    pepperi_api_token = fields.Char(string='Pepperi Api Token', readonly=True)
    pepperi_user_id = fields.Char(string='Pepperi User ID')
    last_order_synch_date = fields.Datetime(string='Last Order Synch Date')
    last_return_synch_date = fields.Datetime(string='Last Return Synch Date')

    last_product_synch_date = fields.Datetime(string='Last Product Synch Date')

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        default=lambda self: self.env.company)
    logging_ids = fields.One2many(
        comodel_name='ir.logging',
        inverse_name='pepperi_account_id',
        string='Loggins', ondelete='set null')
    default_pricelist_id = fields.Many2one('product.pricelist',string='Default Pricelist')
    # --------------
    # Action Methods
    # --------------
    def na_open_wizard_import(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import single order',
            'res_model': 'syd_pepperi.wizard_import_sale_order',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'}

    def action_test_connection(self):
        self.ensure_one()
        result = self._get_pepperi_access_token()
        if result.get('APIToken'):
            raise UserError(_('Connection Test Succeeded! Everything seems properly set up!'))
        raise UserError(_('Connection Test Failed!  %s:' % result.get('error_message')))

    def action_update_access_token(self):
        self.ensure_one()
        result = self._get_pepperi_access_token()
        if result.get('error_message'):
            raise UserError('%s:' % result.get('error_message'))
        self.write({
            'pepperi_company_id': result.get('CompanyID', ''),
            'pepperi_api_token': result.get('APIToken', ''),
            'pepperi_user_id': result.get('UserID', '')
        })

    def action_open_product(self):
        self.ensure_one()
        action_data = self.env.ref('product.product_normal_action_sell').read()[0]
        action_data['domain'] = [('to_pepperi', '=', True)]
        return action_data

    def action_open_customer(self):
        self.ensure_one()
        action_data = self.env.ref('contacts.action_contacts').read()[0]
        action_data['domain'] = [('from_pepperi', '=', True)]
        return action_data

    def action_open_pricelist(self):
        self.ensure_one()
        action_data = self.env.ref('product.product_pricelist_action2').read()[0]
        action_data['domain'] = [('to_pepperi', '=', True)]
        return action_data

    def action_open_transaction(self):
        self.ensure_one()
        action_data = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action_data['domain'] = [('from_pepperi', '=', True)]
        action_data['context'] = {}
        return action_data

    def action_open_pr_price(self):
        self.ensure_one()
        action_data = self.env.ref('product.product_pricelist_item_action').read()[0]
        action_data['domain'] = [('to_pepperi', '=', True)]
        return action_data

    def action_perform_sale_operation(self):
        # _cron_sync_pepperi_sale_order
        # _cron_sync_post_pepperi_sale_order
        # _cron_sync_post_pepperi_products
        self.ensure_one()
        self.env.ref('syd_pepperi.ir_cron_sync_pepperi_order_transaction').sudo().method_direct_trigger()
#         self.env.ref('syd_pepperi.ir_cron_sync_post_pepperi_sale_order').sudo().method_direct_trigger()

    def action_perform_product_operation(self):
        # _cron_sync_pepperi_sale_order
        # _cron_sync_post_pepperi_sale_order
        # _cron_sync_post_pepperi_products
        self.ensure_one()
       
        self.env.ref('syd_pepperi.ir_cron_sync_post_pepperi_products').sudo().method_direct_trigger()
        self.env.ref('syd_pepperi.ir_cron_sync_pepperi_product_stock').sudo().method_direct_trigger()
        
       
    def action_perform_pricelist_operation(self):
        # _cron_sync_pepperi_sale_order
        # _cron_sync_post_pepperi_sale_order
        # _cron_sync_post_pepperi_products
        self.ensure_one()
       
        self.env.ref('syd_pepperi.ir_cron_sync_pepperi_pricelist').sudo().method_direct_trigger()
        self.env.ref('syd_pepperi.ir_cron_sync_pepperi_pricelist_item').sudo().method_direct_trigger()
        

    # ---------------
    # Private Methods
    # ---------------

    @api.model
    def _get_connection(self, domain=[]):
        return self.search(domain, limit=1)

    def _get_pepperi_access_token(self):
        """
            Retrieves company level API Token, Company ID and API Base URI. Requires Admin credentials.
        """
        self.ensure_one()
        return self._synch_with_pepperi(
            http_method='GET', service_endpoint='/company/apitoken',
            params={}, data={})

    def _synch_with_pepperi(self, http_method, service_endpoint, params=None, data=None):
        self.ensure_one()

        if params is None:
            params = {}

        if data is None:
            data = {}

        service_url = '{}/{}{}'.format(self.pepperi_api_url, self.pepperi_api_version, service_endpoint)
        func = '{}:{}'.format(http_method, service_endpoint)
        basic_auth = self._get_pepperi_auth_header()
        headers = self._get_pepperi_request_header()
        response = {}

        try:
            resp = requests.request(
                http_method, service_url,
                auth=basic_auth,
                headers=headers,
                params=params,
                data=json.dumps(data), timeout=TIMEOUT)
            _logger.info('request url : {}'.format(resp.url))
            resp.raise_for_status()
            response = resp.json()
            _logger.info('response from pepperi ::: {}'.format(response))

        except requests.HTTPError as ex:
            level = 'warning'
            if resp.status_code in KNOW_ERROR_CODES:
                message = KNOW_ERROR_CODES[resp.status_code]
            else:
                message = _('Unexpected error ! please report this to your administrator.')
                level = 'error'
            self._log_message(resp.status_code, message, level=level, path=http_method, func=func)
            response['error_message'] = message
        except Exception as ex:
            print(ex)
            message = _('Unexpected error ! please report this to your administrator.')
            level = 'error'
            self._log_message(str(ex), message, level=level, path=http_method, func=func)
            response['error_message'] = _('Unexpected error ! please report this to your administrator.')

        return response

    def _get_token_auth(self):
        """
            return: Base64 String (Header Token - Authorization : 'TokenAuth : apiToken')
        """
        return base64.b64encode(("%s:%s" % ("TokenAuth", self.pepperi_api_token)).encode('UTF-8')).decode('UTF-8')

    def _get_pepperi_request_header(self):
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Catch-Control": "no-cache",
            "X-Pepperi-ConsumerKey": self.pepperi_consumer_key,
        }
        if self.pepperi_api_token:
            header["Authorization"] = 'Basic %s' % self._get_token_auth()
        return header

    def _get_pepperi_auth_header(self):
        return HTTPBasicAuth(self.pepperi_api_login, self.pepperi_api_password)

    def _log_message(self, name, message, level="info", path="/", line="0", func="/"):
        # Usually when we are performing a call to the third party provider to either refresh/fetch transaction/add user, etc,
        # the call can fail and we raise an error. We also want the error message to be logged in the object in the case the call
        # is done by a cron. This is why we are using a separate cursor to write the information on the chatter. Otherwise due to
        # the raise(), the transaction would rollback and nothing would be posted on the chatter.
        with self.pool.cursor() as cr:
            cr.execute("""
                INSERT INTO
                    ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func, pepperi_account_id)
                VALUES
                (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (self.env.uid, 'server', self._cr.dbname, name, level, message, path, line, func, self.id))

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    def get_data_by_uri(self, params={}, data={}, uri='/'):
        """
            Retrieves a single data by internal id..

            uri = /transactions/{InternalID}
            OR
            uri = /items/{InternalID}
            Etc ...

            return data by InternalID
        """
        content = self._synch_with_pepperi(
            http_method='GET', service_endpoint=uri,
            params=params, data=data)
        return content
