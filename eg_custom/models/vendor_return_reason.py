from odoo import fields, models


class VendorReturnReason(models.Model):
    _name = 'vendor.return.reason'
    _description = 'Vendor Return Reason'

    name = fields.Char(string='Title')
    reason_description = fields.Text(string='Reason Description')
