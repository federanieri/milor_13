# -*- coding: utf-8 -*-

from uuid import uuid1

from odoo import fields, models


class OdAS2Stream(models.Model):
    _name = "odas2.stream"

    name = fields.Char(required=True)
    vendor_id = fields.Char(string='Vendor ID', required=True)
    merchant_id = fields.Char(string='Merchant ID')
    sender_id = fields.Char(string='Sender AS2 ID', help="Check Organization AS ID on the gateway")
    receiver_id = fields.Char(string='Receiver AS2 ID', help="Check Partner AS ID on the gateway")
    source_id = fields.Many2one('utm.source', string='UTM Source')
    force_qty = fields.Integer(string='Force product qty to', default=-1,
        help="If lesser than zero then do set qty according to Quantity On Hand.")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, readonly=True, required=True,
        help='The company is automatically set from your user preferences.')
    auto_add_product = fields.Boolean(string='Auto Add to Products', default=True,
        help="If product from CommerceHub not in the products list of the stream then add it.")
    product_ids = fields.Many2many('product.product', string='Products')


class Company(models.Model):
    _inherit = "res.company"

    def _default_odas2_access_token(self):
        return str(uuid1())

    odas2_url = fields.Char(string='OdAS2 Url')
    odas2_test_url_regex = fields.Char(string='OdAS2 Test Url (regex)', default='.*\.test\.')
    odas2_access_token = fields.Char(string='OdAS2 Access Token', default=_default_odas2_access_token)
    odas2_stream_ids = fields.One2many('odas2.stream', 'company_id', string='OdAS2 Receivers')
    odas2_so_partner_id = fields.Many2one('res.partner', string='SO Owner')
    odas2_so_user_id = fields.Many2one('res.users', string='SO Salesperson')
    odas2_so_pricelist_id = fields.Many2one('product.pricelist', string='SO Pricelist')
    odas2_ps_mail_channel_id_when_orphan = fields.Many2one('mail.channel',)
    odas2_pp_force_commercehub_code = fields.Boolean(string='OdAS2 Force CommerceHub Code when similar', default=True)
