# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.tools.safe_eval import safe_eval
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    
    closed = fields.Boolean('Closed',default=False,tracking=True)
    delivery_status = fields.Selection([('to_deliver','To Deliver'),('partial','Partially Delivered'),('delivered','Delivered')],string="Delivery Status",store=True, default="to_deliver", compute="_delivery_status")
    
    @api.depends('order_line.qty_delivered','order_line.product_uom_qty')
    def _delivery_status(self):
        for a in self:
            product_uom_qty_total = sum(v.product_uom_qty for v in a.order_line) 
            delivered_total = sum(v.qty_delivered for v in a.order_line) 
            if delivered_total==0:
                a.delivery_status = 'to_deliver'
            elif product_uom_qty_total>delivered_total:
                a.delivery_status = 'partial'
            else:
                a.delivery_status = 'delivered'
     
    def action_close(self):
        for a in self:
            if a.state not in ('sale','done'):
                raise ValidationError(_('You cannot close draft or sent order'))
            a.closed = True  
            
    def action_open(self):
        for a in self:
            a.closed = False
              
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    
    closed = fields.Boolean('Closed',tracking=True)
    received_status = fields.Selection([('to_receive','To Receive'),('partial','Partially Received'),('received','Received')],string="Received Status",store=True, default="to_receive", compute="_receive_status")
    
    def action_close(self):
        for a in self:
            if a.state not in ('purchase','done'):
                raise ValidationError(_('You cannot close draft or sent order'))
            a.closed = True  
            
    
    def action_open(self):
        for a in self:
            a.closed = False
            
    @api.depends('order_line.qty_received','order_line.product_uom_qty')
    def _receive_status(self):
        for a in self:
            product_uom_qty_total = sum(v.product_uom_qty for v in a.order_line) 
            received_total = sum(v.qty_received for v in a.order_line) 
            if received_total==0:
                a.received_status = 'to_receive'
            elif product_uom_qty_total>received_total:
                a.received_status = 'partial'
                a.date_planned = fields.Datetime.now()
            else:
                a.received_status = 'received'
                a.date_planned = fields.Datetime.now()

                