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

class WizardOrder(models.TransientModel):
    _name = "syd_product_proposal.wizard_order"
    _description = 'Wizard Order'
    
    customer_id = fields.Many2one('res.partner','Customer')
    product_ids = fields.Many2many('product.product',string='Product')
    
    def create_order(self):
        order_line = []
        for p in self.product_ids:
            order_line.append((0,0,{
                               'product_id':p.id,
                               'name':p.name,
                               'product_uom':p.uom_id.id
                               }))
        porder = self.env['proposal.sale.order'].create({
                                       'partner_id':self.customer_id.id,
                                       'porder_line':order_line,
                                       'name':_('New')
                                       })
    
        action = self.env['ir.actions.act_window'].for_xml_id('syd_product_proposal', 'action_proposal_orders')
        action['domain'] = [('id','=',porder.id)]
        action['res_id'] = porder.id
        return action
    
    
