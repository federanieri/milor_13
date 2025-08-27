# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

#Functionality disabled

class StockQuantPackage(models.Model):
    _name = 'stock.quant.package'
    _inherit = ['stock.quant.package', 'syd_os1.doc_os1.mixin']
    
    document_os1_id = fields.Many2one('syd_os1.doc_os1', string="Document OS1", copy=False)
    
    def createDocumentOS1(self):
        partner_id = self.stock_quant_packing_list_ids[0].origin_sale_id.partner_shipping_id
        list_line = []
        list_stock_picking = []
        list_sale_order = []
        
        list_sp_ids = []
        
        for stock_quant_packing in self.stock_quant_packing_list_ids:
            sp_ids = stock_quant_packing.origin_sale_id.picking_ids.filtered(lambda r: bool(r.document_os1_id))
            list_sp_ids.append(sp_ids)
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(sp_ids, list_stock_picking, list_line, list_sale_order, self)
        
        doc_os1_id = self._createDocuemntOS1(list_line, list_stock_picking, list_sale_order, partner_id)
        for sp_ids in list_sp_ids:
            sp_ids.write({'document_os1_id':doc_os1_id.id})
        self.write({'document_os1_id':doc_os1_id.id})
        doc_os1_id.setAnnotazioniCorriere()
        return self._renderView(doc_os1_id)