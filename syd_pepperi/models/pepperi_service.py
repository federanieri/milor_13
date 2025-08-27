# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from base64 import b64encode

_logger = logging.getLogger(__name__)

TIMEOUT = 20




# FIXME : this needs to become an AbstractModel, to be inhereted by google_calendar_service and google_drive_service
class PepperiService(models.TransientModel):
    _name = 'syd_pepperi.pepperi_service'
    _description = 'Pepperi Service'

    
    @api.model
    def sync(self):
        res =self._do_request(uri='/v1.0/company/apitoken',type='GET')
        return res
    
    @api.model
    def _do_request(self, uri, params={}, headers={}, type='POST',):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param uri : the url to contact
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param type : the method to use to make the request
            :param preuri : pre url to prepend to param uri.
        """
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !", (uri, type, headers, params))
        
        Parameters = self.env['ir.config_parameter'].sudo()
        pepperi_base_url = Parameters.get_param('pepperi_base_url')
        consumer_key = Parameters.get_param('pepperi_consumer_key')
        consumer_secret = Parameters.get_param('pepperi_consumer_secret')
        api_token = Parameters.get_param('pepperi_api_token')
        user_pass = b64encode(("%s:%s" % ("TokenAuth", api_token)).encode('UTF-8')).decode('UTF-8')
        headers['Authorization']= 'Basic %s' %  user_pass 
        headers['X-Pepperi-ConsumerKey'] = consumer_key
        ask_time = fields.Datetime.now()
        try:
            if type.upper() in ('GET', 'DELETE'):
                res = requests.request(type.lower(), pepperi_base_url + uri, params=params, headers=headers)
            elif type.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(type.lower(), pepperi_base_url + uri, data=params, headers=headers)
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
                _logger.exception("Bad pepperi request : %s !", error.response.content)
                if error.response.status_code in (400, 401, 410):
                    raise error
                raise ValidationError(_("Something went wrong with your request to pepperi"))
        return (status, response, ask_time)


