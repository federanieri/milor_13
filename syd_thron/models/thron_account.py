# -*- coding: utf-8 -*-

import json
import requests
import logging
from requests.auth import HTTPBasicAuth

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

"""
    Thron Response Code
    When Thron receives a request to an API endpoint, a number of different HTTP status codes can be returned
    in the response depending on the original request.
"""

KNOW_ERROR_CODES = {
    401: _('Unauthorized ! Authentication is required and has failed or has not yet been provided.'),
    403: _('Forbidden! The server is refusing action. The user might not have the necessary permissions for a resource.'),
    400: _('Bad Request! The request is malformed, such as if the body does not parse or some validation fails or semantically incorrect.'),
    404: _('Not Found ! The requested resource could not be found (incorrect or invalid URI).'),
    409: _('Conflict ! The server is refusing action. Already exists a resource with the same identity.'),
    500: _('Internal Server Error ! An internal error occurred in Thron. Please contact to Thron APi Team.'),
    501: _('Not Implemented! The requested endpoint is not available on that particular resource, e.g: currently we do not support POST for the users resource.'),
    504: _('Gateway Timeout! The request could not complete in time. Try breaking it down with our support team.')
}


class ThronAccount(models.Model):
    # Private Attributes
    _name = 'thron.account'
    _description = 'Thron Account'

    # ------------------
    # Fields Declaration
    # ------------------

    name = fields.Char(string='Account Name', required=True)
    thron_client_id = fields.Char(string='Client id', required=True)
    thron_app_id = fields.Char(string='Application id', required=True)
    thron_secret_key = fields.Char(string='Secret key', required=True)
    thron_default_account = fields.Boolean(string='Default account')
    thron_product_api_url = fields.Char(string='Thron product api url', required=True)
    thron_xapi_url = fields.Char(string='Thron Xapi url', required=True)
    thron_api_login = fields.Char(string='Thron api login', required=True)
    thron_api_password = fields.Char(string='Thron api password', required=True)
    thron_api_version = fields.Selection(
        selection=[('v1', 'v1')],
        string='Thron API Version',
        required=True, default='v1')
    thron_api_token = fields.Char(string='Thron Api Token', readonly=True)
    thron_public_api_url = fields.Char(string='Thron Public Api url', required=True)
    thron_public_api_key = fields.Char(string='Thron Public API Key')
    last_synch_date = fields.Datetime(string='Last Synch Date')
    last_product_update_date = fields.Datetime(string='Last Product Update Date')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        default=lambda self: self.env.company)
    logging_ids = fields.One2many(
        comodel_name='ir.logging',
        inverse_name='thron_account_id',
        string='Loggins', ondelete='set null')
    active = fields.Boolean(default=True)

    # --------------
    # Action Methods
    # --------------
  
    def action_open_thron_product(self):
        self.ensure_one()
        action_data = self.env.ref('syd_thron.action_thron_products').read()[0]
        return action_data

    def action_perform_post_products(self):
        Product = self.env['product.product']
        Product.sudo()._cron_sync_post_products()
        
        return True
    
    def action_perform_get_products(self):
        Product = self.env['product.product']
        
        Product.sudo()._cron_sync_get_products()
        
        return True
    
    def action_perform_get_content(self):
        Product = self.env['product.product']
        
        Product.sudo()._cron_sync_get_content()
        return True

    def action_test_connection(self):
        self.ensure_one()
        result = self._get_thron_access_token()
        if result.get('APIToken'):
            raise UserError(_('Connection Test Succeeded! Everything seems properly set up!'))
        raise UserError(_('Connection Test Failed!  %s:' % result.get('error_message')))

    def action_generate_token(self):
        # TODO: take care when this method call from cron
        self.ensure_one()
        result = self._get_thron_access_token()
        if result.get('error_message'):
            raise UserError('%s:' % result.get('error_message'))
        if result.get('resultCode') == 'OK' and result.get('appUserTokenId'):
            self.thron_api_token = result['appUserTokenId']

    # -------------------
    # API Calling Methods
    # -------------------

    def _get_thron_access_token(self):
        """Generate new thron access token"""
        return self._synch_with_thron(
            http_method='POST',
            service_endpoint='api/xadmin/resources/apps/loginApp/{}'.format(self.thron_client_id),
            params={},
            data={'clientId': self.thron_client_id, 'appId': self.thron_app_id, 'appKey': self.thron_secret_key},
            x_request=True,
            token_request=True,
        )

    def _get_thron_header(self, token_request):
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}
        if token_request:
            headers['Content-type'] = 'application/x-www-form-urlencoded'
        else:
            headers['x-tokenid'] = self.thron_api_token
        return headers

    def _get_thron_auth_header(self):
        return HTTPBasicAuth(self.thron_api_login, self.thron_api_password)

    def _synch_with_thron(self, http_method, service_endpoint, params=None, data=None, x_request=False, token_request=False):
        self.ensure_one()

        params = params or {}
        data = data or {}

        if x_request:
            service_url = '{}/{}'.format(self.thron_xapi_url, service_endpoint)
        else:
            service_url = '{}/{}/{}'.format(self.thron_product_api_url, self.thron_api_version, service_endpoint)

        func = '{}:{}'.format(http_method, service_endpoint)
        basic_auth = self._get_thron_auth_header()
        headers = self._get_thron_header(token_request)
        response = {}

        try:
            resp = requests.request(
                http_method, service_url,
                auth=basic_auth,
                headers=headers,
                params=params,
                data=data, timeout=TIMEOUT)
            _logger.info('request url : {}'.format(resp.url))
            resp.raise_for_status()
            response = resp.json()
            _logger.info('response from thron ::: {}'.format(response))

        except requests.HTTPError as ex:
            _logger.error("%s"%(str(ex)),exc_info=True)
            level = 'warning'
            if resp.text:
                text = json.loads(resp.text)
                message = text['message']
            elif resp.status_code in KNOW_ERROR_CODES:
                message = KNOW_ERROR_CODES[resp.status_code]
            else:
                message = _('Unexpected error ! please report this to your administrator.')
                level = 'error'
            self._log_message(resp.status_code, message, level=level, path=http_method, func=func)
            response['error_message'] = message
        except Exception as ex:
            _logger.error("%s"%(str(ex)),exc_info=True)
            message = _('Unexpected error ! please report this to your administrator.')
            level = 'error'
            self._log_message(str(ex), message, level=level, path=http_method, func=func)
            response['error_message'] = _('Unexpected error ! please report this to your administrator.')

        return response

    def _log_message(self, name, message, level="info", path="/", line="0", func="/"):
        # Usually when we are performing a call to the third party provider to either refresh/fetch transaction/add user, etc,
        # the call can fail and we raise an error. We also want the error message to be logged in the object in the case the call
        # is done by a cron. This is why we are using a separate cursor to write the information on the chatter. Otherwise due to
        # the raise(), the transaction would rollback and nothing would be posted on the chatter.
        with self.pool.cursor() as cr:
            cr.execute("""
                INSERT INTO
                    ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func, thron_account_id)
                VALUES
                (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (self.env.uid, 'server', self._cr.dbname, name, level, message, path, line, func, self.id))

    def make_default_account(self):
        self.thron_default_account = True
        self.search([('id', '!=', self.id)]).write({
            'thron_default_account': False
        })

    # products
    def list_products(self, data):
        """ /products/{clientId}
        """

        return self._synch_with_thron(
            http_method='GET',
            service_endpoint='products/{}'.format(self.thron_client_id),
            params={'clientId': self.thron_client_id},
            data=data,
            x_request=False,
        )

    def create_products(self, data):
        """ /products/{clientId}
        """
        return self._synch_with_thron(
            http_method='POST',
            service_endpoint='products/{}'.format(self.thron_client_id),
            params={'clientId': self.thron_client_id},
            data=json.dumps(data),
            x_request=False,
        )

    def update_products(self, data, productId):
        """ /products/{clientId}/{productId}
        """

        return self._synch_with_thron(
            http_method='PUT',
            service_endpoint='products/{}/{}'.format(self.thron_client_id, productId),
            params={'clientId': self.thron_client_id},
            data=data,
            x_request=False,
        )

    def delete_products(self, data, productId):
        """ /products/{clientId}/{productId}
        """

        return self._synch_with_thron(
            http_method='DELETE',
            service_endpoint='products/{}/{}'.format(self.thron_client_id, productId),
            params={'clientId': self.thron_client_id},
            data=data,
            x_request=False,
        )

    # productupdatejobs
    def list_product_update_jobs(self, ids=None, cursor=None, limit=None):
        """ /productupdatejobs/{clientId}
        """

        data = {}
        return self.call(endpoint="productupdatejobs", data=data)

    def create_product_update_jobs(self):
        """ /productupdatejobs/{clientId}
        """

        data = {}
        return self.call(endpoint="productupdatejobs", data=data)

    # productdeletejobs
    def list_products_delete_jobs(self, ids=None, cursor=None, limit=None):
        """ /productdeletejobs/{clientId}
        """

        data = {}
        return self.call(endpoint="productdeletejobs", data=data)

    def create_product_delete_jobs(self):
        """ /productdeletejobs/{clientId}
        """

        data = {}
        return self.call(endpoint="productdeletejobs", data=data)

    # search
    def search_products(self, data):
        """ /search/products/{clientId}
        """

        return self._synch_with_thron(
            http_method='POST',
            service_endpoint='search/products/{}'.format(self.thron_client_id),
            params={'clientId': self.thron_client_id},
            data=json.dumps(data),
            x_request=False,
        )

    # Search Content
    def search_content(self, data):
        """/xcontents/resources/content/search/{clientID}
        """
        return self._synch_with_thron(
            http_method='POST',
            service_endpoint='api/xcontents/resources/content/search/{}'.format(self.thron_client_id),
            params={},
            data=json.dumps(data),
            x_request=True,
        )

    # internalS3files
    def upload_an_import_CSV_file(self):
        """ /internalS3files/{clientId}
        """

        data = {}
        return self.call(endpoint="internalS3files", data=data)

    # productimports
    def list_product_import_jobs(self):
        """ /productimports/{clientId}
        """

        data = {}
        return self.call(endpoint="productimports", data=data)

    def create_import_jobs(self):
        """ /productimports/{clientId}
        """

        data = {}
        return self.call(endpoint="productimports", data=data)

    def list_failed_import_rows(self):
        """ /productimports/{clientId}/{importId}/failedrows
        """

        data = {}
        return self.call(endpoint="productimports", data=data)
