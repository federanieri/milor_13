# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models
import base64
import requests


class NaApiSyncEnv(models.Model):
    _name = 'na.api.sync.env'

    name = fields.Char('Environment Name', required=True)
    api_type = fields.Selection([('con', 'Connect to external API'),
                                 ('exp', 'Expose API from Odoo'),
                                 ('both', 'Connect to external API and expose from Odoo'),
                                 ('import_feed', 'Import from Data Feed'),
                                 ('export_feed', 'Export Data Feed')],
                                default='con', string='Sync Type', required=True)
    auth_type = fields.Selection([('up', 'Username and Password'), ('api_key', 'API Key'),
                                  ('oauth2', 'OAuth 2.0')], string='Authentication Type')
    api_key = fields.Char(string='API Key')
    username = fields.Char(string='Username')
    password = fields.Char(string='Password')
    token_url = fields.Char(string='Token URL')
    access_token = fields.Char(string='Access Token')
    accept = fields.Char(string='Accept')
    content_type = fields.Char(string='Content Type')
    authorization_scope = fields.Char(string='Authorization Scope')
    log_days = fields.Integer(string='Log Days', default=7, required=True)
    config_ids = fields.One2many('na.api.sync.config', 'env_id', string='Synchronizations')

    def get_headers(self, api_logger):
        header = {}
        if self.accept:
            header['Accept'] = self.accept
        if self.content_type:
            header['Content-Type'] = self.content_type
        if self.authorization_scope:
            header['Authorization-Scope'] = self.authorization_scope
        if self.auth_type == 'up':
            if not self.username or not self.password:
                api_logger.log_msg = 'The credentials are not configured, you can do it in the environment settings'
                return False
            auth_string = f"{self.username}:{self.password}"
            auth_string_encoded = base64.b64encode(auth_string.encode()).decode('utf-8')
            header['Authorization'] = f"Basic {auth_string_encoded}"
        elif self.auth_type == 'api_key':
            if not self.api_key:
                api_logger.log_msg = 'The API key is not configured, you can do it in the environment settings'
                return False
            header['Authorization'] = 'Basic ' + self.api_key
        elif self.auth_type == 'oauth2':
            try:
                # TODO: Vedere se rendere configurabile
                token_header = {'Content-Type': 'application/x-www-form-urlencoded'}
                payload = 'grant_type=password&username={}&password={}'.format(self.username, self.password)
                response = requests.post(self.token_url, headers=token_header, data=payload)
                if response.status_code == 200:
                    rj = response.json()
                    if 'access_token' in rj:
                        self.access_token = rj['access_token']
                        header['Authorization'] = 'Bearer ' + self.access_token
                else:
                    self.env['na.api.sync.log'].create({
                        'env_id': self.id,
                        'log_msg': 'There was an error during request for Access Token'
                    })
            except:
                self.env['na.api.sync.log'].create({
                    'env_id': self.id,
                    'log_msg': 'There was an error during request for Access Token'
                })
        return header
