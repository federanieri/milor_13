# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'syd_os1.doc_os1.mixin']
    
    has_doc_os1 = fields.Boolean('Ha un DOC OS1')
    doc_os1_ids = fields.Many2many('syd_os1.doc_os1', 'sale_order_document_rel', 'sale_order_id', 'document_os1_id',
                                        string='documenti OS1', copy=False)
    proFormaType = fields.Boolean('Pro Forma')
    
    def setProFormaType(self):
        if self.proFormaType:
            self.proFormaType = False
        else:
            self.proFormaType = True
    
    def createDocumentOS1(self):
        partner_id = False
        list_line = []
        list_stock_picking = []
        list_sale_order = []
        
        list_sp_ids = []
        
        for so in self:
            if bool(so.doc_os1_ids):
                raise UserError("Questo Ordine: {} ha già un DOC OS1".format(so.display_name))
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(False, list_stock_picking, list_line, list_sale_order, so.display_name, so)
        doc_os1_id = self._createDocuemntOS1(list_line, list_stock_picking, list_sale_order, partner_id)
        
        self.write({'doc_os1_ids':[[4, doc_os1_id.id]],
                    'has_doc_os1':True})
        doc_os1_id.setAnnotazioniCorriere()
        return self._renderView(doc_os1_id)
    
    
class ReturnOrder(models.Model):
    _name = 'return.order'
    _inherit = ['return.order', 'syd_os1.doc_os1.mixin']
    
    doc_os1_ids = fields.Many2many('syd_os1.doc_os1', 'return_order_document_rel', 'return_order_id', 'document_os1_id',
                                        string='documenti OS1')
    doc_os1_state = fields.Selection([('no_one','No one'),
                                      ('draft', 'Draft'),
                                      ('validate', 'Validate'),
                                      ('done', 'Done'),
                                      ('invoiced', 'Invoiced'),
                                      ('paid', 'Paid')], string='State of Doc OS1', compute="_get_doc_os1_state")
    def _get_doc_os1_state(self):
        for a in self:
            state = 'no_one'
            for d in a.doc_os1_ids:
                state = d.state
            a.doc_os1_state = state
    
    def createDocumentOS1(self):
        partner_id = False
        list_line = []
        list_stock_picking = []
        list_sale_order = []
        
        list_sp_ids = []
        for so in self:
            sp_ids = so.incoming_delivery_id.filtered(lambda r: r.picking_type_id.code == 'incoming' and r.state in ['assigned','done'] and not bool(r.document_os1_id))
            list_sp_ids.append(sp_ids)
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(sp_ids, list_stock_picking, list_line, list_sale_order, so.display_name, so)
        doc_os1_id = self._createDocuemntOS1(list_line, list_stock_picking, list_sale_order, partner_id)
        
        for sp_ids in list_sp_ids:
            sp_ids.write({'document_os1_id':doc_os1_id.id})
        
        self.write({'doc_os1_ids':[[4, doc_os1_id.id]]})
        doc_os1_id.setAnnotazioniCorriere()
        return self._renderView(doc_os1_id)