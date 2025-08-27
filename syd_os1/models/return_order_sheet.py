# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


    
class ReturnOrder(models.Model):
    _name = 'return.order.sheet'
    _description = 'Return Order Sheet'
    _inherit = ['return.order.sheet', 'syd_os1.doc_os1.mixin']
    
    doc_os1_ids = fields.Many2many('syd_os1.doc_os1', 'return_order_sheet_document_rel', 'return_order_sheet_id', 'document_os1_id',
                                        string='documenti OS1')
    doc_os1_state = fields.Selection([
        ('no_one','No one'),
        ('draft', 'Draft'),
        ('validate', 'Validate'),
        ('done', 'Done'),
        ('ddt','DDT'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid')
        ], string='State of Doc OS1', compute="_get_doc_os1_state")
    
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
        for ros in self:
            if not all([a.invoice_code for a in ros.return_order_line_ids]):
                raise ValidationError(_('Not all line have invoice specified'))
            sp_ids = ros.picking_ids.filtered(lambda r: r.picking_type_id.code == 'incoming' and r.state in ['assigned','done'] and not bool(r.document_os1_id))
            list_sp_ids.append(sp_ids)
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(sp_ids, list_stock_picking, list_line, list_sale_order, ros.display_name)
        for line in list_line:
            line[2]['crma_id'] = self.id
        doc_os1_id = self._createDocuemntOS1(list_line, list_stock_picking, list_sale_order, partner_id)
        
        for sp_ids in list_sp_ids:
            sp_ids.write({'document_os1_ids':[[4,doc_os1_id.id]]})
        
        self.write({'doc_os1_ids':[[4, doc_os1_id.id]],
                    'state':'done'})
        doc_os1_id.setAnnotazioniCorriere()
        doc_os1_id.testInfoHeaderInvoice()
        return self._renderView(doc_os1_id)