# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'syd_os1.doc_os1.mixin']
    
    document_os1_id = fields.Many2one('syd_os1.doc_os1', string="Document OS1 id", copy=False)
    document_os1_ids = fields.Many2many('syd_os1.doc_os1', 'sp_doc_os1_rel', string="Document OS1 ids", copy=False)
    document_os1_internal_id = fields.Many2one('syd_os1.doc_os1', string="Document OS1", copy=False)
    code_type_picking = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer')], 'Type of Operation code', related = "picking_type_id.code")
    payment_gateway_order = fields.Many2one(related="sale_id.shopify_payment_gateway_id")

    def action_auto_create_docos1(self):
        for sp in self:
            try:
                if sp.picking_type_id.code == 'internal' and sp.picking_type_id.sequence_code == 'PACK':
                    sp.createDocumentOS1()
            except Exception as error:
                _logger.info("E' andato qualcosa storto per il trasferimento: {}".format(sp.display_name))
    
    def createDocumentOS1(self):
        partner_id = False
        list_line = []
        list_stock_picking = []
        list_sale_order = []
        sp_internal_ids = False
        
        list_name_picking = []
        
        type_sp = False
        error_type_sp = {}
        yes_error_type_sp = False
        for sp in self:
            list_name_picking.append(sp.display_name)
            if not bool(type_sp):
                type_sp = sp.picking_type_id.code
            if type_sp != sp.picking_type_id.code:
                yes_error_type_sp = True
            if sp.display_name not in error_type_sp:
                error_type_sp[sp.display_name] = []
            error_type_sp[sp.display_name].append(sp.picking_type_id.code)
        
        if bool(yes_error_type_sp):
            raise UserError("I trasferimenti selezionati non sono dello stesso tipo:\n{}".format(error_type_sp))
        
        
        
        different_type_sp_dest = False 
        if type_sp == 'internal':
            sp_internal_ids = self.filtered(lambda r: not bool(r.document_os1_internal_id))
            sp_wt_doc_os1_ids = self.filtered(lambda r: bool(r.document_os1_internal_id))
            if bool(sp_wt_doc_os1_ids):
                list_wt_doc_os1 = []
                for sp in sp_wt_doc_os1_ids:
                    list_wt_doc_os1.append(sp.display_name)
                raise UserError("I trasferimenti selezioanti hanno già un DOC OS1 associato.\n{}".format(",".join(str(i) for i in list_wt_doc_os1)))
            type_sp_dest = False
            sp_ids = self.env['stock.picking']
            listNameSPInternal = []
            for sp_internal in sp_internal_ids:
                listNameSPInternal.append(sp_internal.display_name)
                sp_ids_local = False
                if sp_internal.state != 'done':
                    raise UserError("I trasferimento {} selezionato non è validato.".format(sp_internal.display_name))
                there_is_outing = False
                for sm_internal in sp_internal.move_ids_without_package:
                    for sm_dest in sm_internal.move_dest_ids:
                        if not bool(sp_ids_local):
                            sp_ids_local = sm_dest.picking_id
                        else:
                            if not sm_dest.picking_id in sp_ids_local:
                                sp_ids_local += sm_dest.picking_id
                        if sm_dest.picking_id.picking_type_id.code == 'outgoing' and not bool(there_is_outing):
                            there_is_outing = True
                        if not bool(type_sp_dest):
                            type_sp_dest = sm_dest.picking_id.picking_type_id.code
                        if type_sp_dest != sm_dest.picking_id.picking_type_id.code:
                            different_type_sp_dest = True
                if bool(sp_ids_local) and bool(there_is_outing):
                    sp_ids += sp_ids_local
                else:
                    raise UserError('Il trasferimento {} non è collegato a nessun trasferimento OUT'.format(sp_internal.display_name))
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(sp_internal_ids, list_stock_picking, list_line, list_sale_order, ",".join(str(i) for i in listNameSPInternal))
        elif type_sp == 'outgoing' or type_sp == 'incoming':
            sp_ids = self.filtered(lambda r: not bool(r.document_os1_internal_id))
            sp_wt_doc_os1_ids = self.filtered(lambda r: bool(r.document_os1_internal_id))
            if bool(sp_wt_doc_os1_ids):
                list_wt_doc_os1 = []
                for sp in sp_wt_doc_os1_ids:
                    list_wt_doc_os1.append(sp.display_name)
                raise UserError("I trasferimenti selezioanti hanno già un DOC OS1 associato.\n{}".format(",".join(str(i) for i in list_wt_doc_os1)))
            listNameSP = []
            for sp in sp_ids:
                listNameSP.append(sp.display_name)
            list_stock_picking, list_line, list_sale_order, partner_id = self._forStockPicking(sp_ids, list_stock_picking, list_line, list_sale_order, ",".join(str(i) for i in listNameSP))
        else:
            raise UserError("I trasferimenti selezionati non sono del tipo PACK o OUT o RC.\n{}".format(",".join(str(i) for i in list_name_picking)))
        
        doc_os1_id = self._createDocuemntOS1(list_line, list_stock_picking, list_sale_order, partner_id)
        sp_ids.write({'document_os1_ids':[[4,doc_os1_id.id]]})
        for sp in sp_ids:
            ro = self.env['return.order'].search([('incoming_delivery_id','=',sp.id)])
            if bool(ro):
                ro.write({'doc_os1_ids':[[4, doc_os1_id.id]]})
        if bool(sp_internal_ids):
            sp_internal_ids.write({'document_os1_internal_id':doc_os1_id.id})
            doc_os1_id.idTransportType()
            doc_os1_id.forwarder()
            doc_os1_id.getAspettoBeni()
        doc_os1_id.setAnnotazioniCorriere()
        if bool(different_type_sp_dest):
            doc_os1_id.write({'message_creation':'I trasferimenti di destinazione non sono dello stesso tipo'})
        return self._renderView(doc_os1_id)