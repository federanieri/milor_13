# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError
from odoo.http import request


_logger = logging.getLogger(__name__)

# FIXME : this needs to become an AbstractModel, to be inhereted by google_calendar_service and google_drive_service
class ThronService(models.TransientModel):
    _name = 'syd_thron.thron_service'
    _description = 'Thron Service'

    @api.model
    def generate_refresh_token(self, service, authorization_code):
        """ Call Google API to refresh the token, with the given authorization code
            :param service : the name of the google service to actualize
            :param authorization_code : the code to exchange against the new refresh token
            :returns the new refresh token
        """
        Parameters = self.env['ir.config_parameter'].sudo()
        client_id = Parameters.get_param('google_%s_client_id' % service)
        client_secret = Parameters.get_param('google_%s_client_secret' % service)
        redirect_uri = Parameters.get_param('google_redirect_uri')

        # Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorization_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': "authorization_code"
        }
        try:
            req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
            content = req.json()
        except IOError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

        return content.get('refresh_token')

    

    # TODO JEM : remove preuri param, and rename type into method
    @api.model
    def _do_request(self, uri, params={}, headers={}, type='POST', preuri="https://www.googleapis.com"):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param type : the method to use to make the request
            :param preuri : pre url to prepend to param uri.
        """
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !", (uri, type, headers, params))

        ask_time = fields.Datetime.now()
        try:
            if type.upper() in ('GET', 'DELETE'):
                res = requests.request(type.lower(), preuri + uri, params=params, timeout=TIMEOUT)
            elif type.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(type.lower(), preuri + uri, data=params, headers=headers, timeout=TIMEOUT)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!') % (type))
            res.raise_for_status()
            status = res.status_code

            if int(status) in (204, 404):  # Page not found, no response
                response = False
            else:
                response = res.json()

            try:
                ask_time = datetime.strptime(res.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
            except:
                pass
        except requests.HTTPError as error:
            if error.response.status_code in (204, 404):
                status = error.response.status_code
                response = ""
            else:
                _logger.exception("Bad google request : %s !", error.response.content)
                if error.response.status_code in (400, 401, 410):
                    raise error
                raise self.env['res.config.settings'].get_config_warning(_("Something went wrong with your request to google"))
        return (status, response, ask_time)

    # TODO : remove me, it is only used in google calendar. Make google_calendar use the constants
    @api.model
    def get_client_id(self, service):
        return self.env['ir.config_parameter'].sudo().get_param('google_%s_client_id' % (service,), default=False)
