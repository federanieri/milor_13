import logging
import requests
import json
from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    use_poste_italiane_shipping_provider = fields.Boolean(copy=False,
                                                          string="Are You Use Poste Italiane Shipping Provider.?",
                                                          help="If use Poste Italiane shipping provider than value set TRUE.",
                                                          default=False)
    poste_italiane_api_url = fields.Char(string="API URL", copy=False, default="https://apiw.gp.posteitaliane.it/gp/internet")
    poste_italiane_client_id = fields.Char(string="Client ID", copy=False)
    poste_italiane_client_secret = fields.Char(string="secret ID", copy=False)
    poste_italiane_access_token = fields.Char(string="Access Token", copy=False, readonly=True)

    def get_poste_italiane_token(self):
        try:
            api_url = "%s/user/sessions"%(self.poste_italiane_api_url)
            payload = json.dumps({
                "client_id": "%s"%(self.poste_italiane_client_id),
                "secretId": "%s"%(self.poste_italiane_client_secret),
                "audience": "api://8f0f2c58-19a8-45ef-9f9e-8bcb0acc7657/.default",
                "grant_type": "client_credentials"
            })
            headers = {
                'Content-Type': 'application/json',
                'POSTE_clientID':"%s"%(self.poste_italiane_client_id)
            }
            response_data = requests.request("POST", url=api_url, headers=headers, data=payload)
            _logger.info(">>> Response Data {}".format(response_data))
            if response_data.status_code in [200, 201]:
                json_response = response_data.json()
                self.poste_italiane_access_token = json_response.get("access_token")
            else:
                raise ValidationError(response_data.text)
        except Exception as e:
            raise ValidationError(e)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Token Get successfully!",
                'img_url': '/web/static/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def poste_italiane_token_using_crone(self, ):
        for credential_id in self.search([]):
            try:
                if credential_id.use_poste_italiane_shipping_provider:
                    credential_id.get_poste_italiane_token()
            except Exception as e:
                _logger.info("Getting an error in Generate Token request Odoo to Poste Italiane: {0}".format(e))