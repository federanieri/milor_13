# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class ManageEan(models.Model):
    _name = "manage.ean"
    _description = "Relation between EAN codes and products"
    
    product_id = fields.Many2one('product.product', string = "Product", readonly=True)
    ean = fields.Many2one('assign.ean',string = "EAN", default = lambda self: self._default_ean(), required = True) 
    link_date = fields.Date(string = "Link Date", readonly=True)
    
    @api.model
    def create(self, vals):
        change_ean_id = super(ManageEan, self).create(vals)
#         change_ean_id.product_id.barcode = change_ean_id.ean.name
        change_ean_id.ean.product_id = change_ean_id.product_id.id
        
        if bool(change_ean_id.product_id) and not bool(change_ean_id.link_date): 
            change_ean_id.ean.link_date = datetime.today()
        else:
            change_ean_id.ean.link_date = change_ean_id.link_date
        
        display_msg = """ The product """ + change_ean_id.product_id.name + """, has been assigned to EAN number """  + str(change_ean_id.ean.name) + """ on the """ + str(change_ean_id.ean.link_date)
        change_ean_id.product_id.message_post(body = display_msg)
        change_ean_id.ean.message_post(body=display_msg)
        
        return change_ean_id
    
    def _default_ean(self):
        select_ean_id = self.env['assign.ean'].search([('product_id', '=', False)], limit=1)
        return select_ean_id.id
        
class AssignEan(models.Model):
    _name = 'assign.ean'
    _inherit = ['mail.thread']
    _description = "New EAN has been created"
    _sql_constraints = [('ean_uniq', 'unique(ean)', 'EAN must be unique')]
    _order = 'id'
    
    name = fields.Char(string = "name", related = "ean")
    product_id = fields.Many2one('product.product', 'Products')
    ean = fields.Char(string = "EAN", required = True) 
    link_date = fields.Date(string = "Link Date", default = datetime.today())
    unlink_date = fields.Date(string = "Unlink Date", readonly=True) 
    assign_problem = fields.Boolean('Assign Problem',store=True,compute="_assign_problem")
    
    @api.depends('product_id.barcode','ean')
    def _assign_problem(self):
        for a in self:
            a.assign_problem = a.product_id.barcode == a.ean
        
    @api.model
    def create(self, vals):
        assign_ean_id = super(AssignEan, self).create(vals)
#         assign_ean_id.product_id.barcode = assign_ean_id.ean
        
        if bool(assign_ean_id.product_id):
            self.env['manage.ean'].create({'product_id':assign_ean_id.product_id.id, 'ean':assign_ean_id.id, 'link_date': assign_ean_id.link_date})
        return assign_ean_id

    def unlink(self):
        for move in self:
            to_unlink = self.env['manage.ean'].search([('ean', '=', move.id)])
            select_product_id = self.env['product.product'].search([('barcode', '=', move.ean)]) 
#             select_product_id.barcode = False
            to_unlink.unlink()
        return super(AssignEan, self).unlink()
    
    
    def action_force_ean(self):
        for a in self:
            if bool(a.product_id):
                a.product_id.barcode = a.ean
                
    def delete_product(self):
        for a in self:
            if bool(a.product_id):
                delete_product_id = self.env['product.product'].search([('barcode', '=', a.ean)])
                delete_manage_product = self.env['manage.ean'].search([('product_id', '=', a.product_id.id)])          
                
                delete_product_id.write({'barcode':False})
                self.write({'product_id':False, 'link_date':False, 'unlink_date':datetime.today()})
                
                display_msg = """ The product """ +  delete_manage_product.product_id.name + """, has been unassigned on the """ + str(a.unlink_date)
                delete_manage_product.ean.message_post(body = display_msg)   
                delete_product_id.message_post(body = display_msg)     
                
                delete_manage_product.unlink()      
            
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    
    ean_ids = fields.One2many('assign.ean','product_id',string="")
    
    def delete_ean(self):
        for a in self:
            if a.barcode:
                delete_ean_id = self.env['manage.ean'].search([('product_id', '=', a.id)])
                
                a.write({'barcode':False})
    
                delete_assign_ean = self.env['assign.ean'].search([('product_id', '=', a.id)])
                delete_assign_ean.write({'link_date': False, 'product_id': False, 'unlink_date':datetime.today()})
        
                display_msg = """ The product """ + str(delete_ean_id.product_id.name) + """, has been unassigned on the """ + str(delete_assign_ean.unlink_date)
                
                delete_ean_id.product_id.message_post(body = display_msg)           
                delete_ean_id.ean.message_post(body=display_msg)
                
                delete_ean_id.unlink()


    def assign_ean_auto(self):
        for a in self:
            select_ean_id = self.env['assign.ean'].search([('product_id', '=', False)], limit=1) 
            if bool(select_ean_id):
                select_manage_ean = self.env['manage.ean'].create({'product_id':a.id, 'ean':select_ean_id.id, 'link_date':select_ean_id.link_date})
                
                self.barcode = select_ean_id.ean 
                select_ean_id.write({'product_id':a.id, 'link_date':datetime.today(), 'unlink_date':False})              
                            
            else: 
                notification = {'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': ('WARNING'),
                                    'message': 'No EAN available, please refresh the page',
                                    'type':'warning',
                                    'sticky': True }
                                }
                return notification
            
            
            
       
