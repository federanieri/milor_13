# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class returnReasons(models.Model):
    _name = "return.order.reason"
    _description = "Return Order Reasons"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin'] 

    reason_code = fields.Char('Reason Code')
    name = fields.Text('Return Order Reason', translate=True,help="Reason for a customer to return an order.",
                              placeholder="Start typing...")
    reason_for = fields.Selection(selection=lambda x: x.get_return_order_types(), string="Use for Return type:")
    
    def get_return_order_types(self):
        return self.env['return.order.sheet']._fields['return_type'].selection + [('all','All')]
