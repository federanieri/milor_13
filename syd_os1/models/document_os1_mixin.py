# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class DocumentOS1Mixin(models.AbstractModel):
    _name = 'syd_os1.doc_os1.mixin'
    _description = 'document OS1 Mixin'
    
    def testComplianceStockPicking(self, stock_picking_ids, sale_order_ids=False):
        partner_id = False
        
        error_partner_id = {}
        is_error_partner_id = False
        
        error_state = {}
        is_error_state = False
        
        error_doc_os1 = []
        if bool(stock_picking_ids):
            for stock_picking_id in stock_picking_ids:
                if not bool(partner_id):
                    partner_id = stock_picking_id.partner_id
                if stock_picking_id.display_name not in error_partner_id:
                    error_partner_id[stock_picking_id.display_name] = []
                error_partner_id[stock_picking_id.display_name].append(stock_picking_id.partner_id.display_name)
                if stock_picking_id.partner_id.id != partner_id.id:
                    is_error_partner_id = True
                
                if stock_picking_id.display_name not in error_state:
                    error_state[stock_picking_id.display_name] = []
                error_state[stock_picking_id.display_name].append(stock_picking_id.state)
                if stock_picking_id.state not in ['assigned','done'] :
                    is_error_state = True
                
                if bool(stock_picking_id.document_os1_id):
                    error_doc_os1.append(stock_picking_id.display_name)
        elif bool(sale_order_ids):
            for sale_order_id in sale_order_ids:
                if not bool(partner_id):
                    partner_id = sale_order_id.partner_id
                if sale_order_id.partner_id.id != partner_id.id:
                    error_partner_id.append(sale_order_id.display_name)
        else:
            raise UserError("Errore non ci sono ne trasferimenti ne Ordini")
        
        message_error = ''
        if bool(is_error_partner_id):
            message_error = '{}Hai selezionato delle operazioni che non sono dello stesso cliente\n{}\n'.format(message_error, error_partner_id)
        if bool(is_error_state):
            message_error = "{}Hai selezionato delle operazioni che non sono nello stato 'Pronto'\n{}\n".format(message_error, error_state)
        if len(error_doc_os1) != 0:
            message_error = '{}Hai selezionato delle operazioni che hanno già un documento OS1 legato\n\n{}\n'.format(message_error, ",".join(str(i) for i in error_doc_os1))
        
        if bool(message_error):
            raise UserError(message_error)
        
        return partner_id
    
    def getOriginSaleLineId(self, stock_move):
        origin_sale_line_id = False
        if bool(stock_move.origin_sale_line_id):
            origin_sale_line_id = stock_move.origin_sale_line_id
        elif bool(stock_move.total_grouped_sale_line_ids):
            origin_sale_line_id = stock_move.total_grouped_sale_line_ids[0]
        return origin_sale_line_id
    
    def calc_z_product(self, milor_account_code):
        z_product = False
        if bool(milor_account_code):
            z_product = milor_account_code.lower() == 'z'
        return z_product
    
    def get_row_type(self, stock_move, account_os1, sale_order_line_id=False):
        if not bool(sale_order_line_id):
            origin_sale_line_id = self.getOriginSaleLineId(stock_move)
            if bool(origin_sale_line_id):
                if not bool(origin_sale_line_id.free_product):
                    if bool(stock_move.sale_price):
                        hts_price = stock_move.sale_price
                    else:
                        if account_os1.company_id.account_code_os1 == 'milor_account_code':
                            z_product = self.calc_z_product(stock_move.product_id.milor_account_code)
                        else:
                            z_product = self.calc_z_product(stock_move.product_id.milor_account_code_id.name if stock_move.product_id.milor_account_code_id else False)
                        if z_product:
                            hts_price = stock_move.product_id.hts_price
                        else:
                            hts_price = stock_move.price

                    if account_os1.company_id.account_code_os1 == 'milor_account_code':
                        z_product = self.calc_z_product(origin_sale_line_id.product_id.milor_account_code)
                    else:
                        z_product = self.calc_z_product(origin_sale_line_id.product_id.milor_account_code_id.name if origin_sale_line_id.product_id.milor_account_code_id else False)
                    
                    if bool(origin_sale_line_id.discount) and not z_product:
                        hts_price = hts_price - ((hts_price * origin_sale_line_id.discount)/100)
                    if origin_sale_line_id.product_id.id in self.env['product.product'].search([('categ_id','child_of',account_os1.categ_product_packaging_id.id)]).ids:
                        if origin_sale_line_id.order_id.partner_id.country_id.id == self.env['res.country'].search([('code','=','IT')]).id:
                            row_type = '73'
                        else:
                            row_type = '3'
                    else :
                        row_type = '1'
                else:
                    hts_price = stock_move.product_id.hts_price

                    if account_os1.company_id.account_code_os1 == 'milor_account_code':
                        z_product = self.calc_z_product(stock_move.product_id.milor_account_code)
                    else:
                        z_product = self.calc_z_product(stock_move.product_id.milor_account_code_id.name if stock_move.product_id.milor_account_code_id else False)
                    
                    if bool(origin_sale_line_id.discount) and not z_product:
                        hts_price = hts_price - ((hts_price * origin_sale_line_id.discount)/100)
                    row_type = '11'
            else:
                if bool(stock_move.sale_price):
                    hts_price = stock_move.sale_price
                else:
                    if account_os1.company_id.account_code_os1 == 'milor_account_code':
                        z_product = self.calc_z_product(stock_move.product_id.milor_account_code)
                    else:
                        z_product = self.calc_z_product(stock_move.product_id.milor_account_code_id.name if stock_move.product_id.milor_account_code_id else False)
                    
                    if z_product:
                        hts_price = stock_move.product_id.hts_price
                    else:
                        hts_price = stock_move.price
                if stock_move.product_id.id in self.env['product.product'].search([('categ_id','child_of',account_os1.categ_product_packaging_id.id)]).ids:
                    if stock_move.picking_id.partner_id.country_id.id == self.env['res.country'].search([('code','=','IT')]).id:
                        row_type = '73'
                    else:
                        row_type = '3'
                else :
                    row_type = '1'
        else:
            if not bool(sale_order_line_id.free_product):
                if account_os1.company_id.account_code_os1 == 'milor_account_code':
                    z_product = self.calc_z_product(sale_order_line_id.product_id.milor_account_code)
                else:
                    z_product = self.calc_z_product(sale_order_line_id.product_id.milor_account_code_id.name if sale_order_line_id.product_id.milor_account_code_id else False)
                
                if not z_product:
                    hts_price = sale_order_line_id.price_unit
                    if bool(sale_order_line_id.discount):
                        hts_price = hts_price - ((hts_price * sale_order_line_id.discount)/100)
                else:
                    hts_price = sale_order_line_id.product_id.hts_price
                if sale_order_line_id.product_id.id in self.env['product.product'].search([('categ_id','child_of',account_os1.categ_product_packaging_id.id)]).ids:
                    if sale_order_line_id.order_id.partner_id.country_id.id == self.env['res.country'].search([('code','=','IT')]).id:
                        row_type = '73'
                    else:
                        row_type = '3'
                else :
                    row_type = '1'
            else:
                if account_os1.company_id.account_code_os1 == 'milor_account_code':
                    z_product = self.calc_z_product(sale_order_line_id.product_id.milor_account_code)
                else:
                    z_product = self.calc_z_product(sale_order_line_id.product_id.milor_account_code_id.name if sale_order_line_id.product_id.milor_account_code_id else False)
                
                if not z_product:
                    hts_price = sale_order_line_id.product_id.hts_price
                    if bool(sale_order_line_id.discount):
                        hts_price = hts_price - ((hts_price * sale_order_line_id.discount)/100)
                else:
                    hts_price = sale_order_line_id.product_id.hts_price
                row_type = '11'
        return row_type, hts_price, origin_sale_line_id if not bool(sale_order_line_id) else False
    
    def get_anno_numero_rif(self, stock_move, AnnoRif, NumeroRif, sezionale='', full_date = False, invoice_id = False):
        if invoice_id:
            AnnoRif = str(invoice_id.invoice_date.year)
            list_NumeroRif = invoice_id.name.split('/')
            NumeroRif = list_NumeroRif[0]
            sezionale = list_NumeroRif[1] if list_NumeroRif[1] else sezionale
            full_date = invoice_id.invoice_date
        elif stock_move:
            if stock_move.origin_ro_line_id:
                if bool(stock_move.origin_ro_line_id.origin_invoice_id):
                    AnnoRif = str(stock_move.origin_ro_line_id.origin_invoice_id.invoice_date.year)
                    list_NumeroRif = stock_move.origin_ro_line_id.origin_invoice_id.name.split('/')
                    NumeroRif = list_NumeroRif[0]
                    sezionale = list_NumeroRif[1] if list_NumeroRif[1] else sezionale
                    full_date = stock_move.origin_ro_line_id.origin_invoice_id.invoice_date
                else:
                    if bool(stock_move.origin_ro_line_id.invoice_code):
                        list_NumeroRif = stock_move.origin_ro_line_id.invoice_code.split('/')
                        NumeroRif = list_NumeroRif[0]
                        sezionale = list_NumeroRif[1] if list_NumeroRif[1] else sezionale
                    if stock_move.origin_ro_line_id.date_invoice:
                        AnnoRif = str(stock_move.origin_ro_line_id.date_invoice.year)
                    full_date = stock_move.origin_ro_line_id.date_invoice
        return AnnoRif, NumeroRif, sezionale, full_date
    
    def get_vals_line(self, stock_move, hts_price, origin_sale_line_id, quantity, row_type, origins, sale_order_line_id):
        AnnoRif, NumeroRif = '0', '0'
        sezionale = ''
        full_date = False
        
        if bool(sale_order_line_id):
            return [
                [0, 0, {
                    'product_id':sale_order_line_id.product_id.id,
                    'quantity':quantity,
                    'price_unit':sale_order_line_id.price_unit,
                    'price_htc':hts_price,
                    'price_subtotal':sale_order_line_id.price_subtotal,
                    'sale_order_line_id':sale_order_line_id.id,
                    'stock_move_id':False,
                    'IdIva':sale_order_line_id.tax_id.id,
                    'discount':sale_order_line_id.discount,
                    'note':'HTS CODE {}'.format(sale_order_line_id.product_id.hts_id.code) if bool(sale_order_line_id.product_id.hts_id) and bool(sale_order_line_id.product_id.hts_id.code) else '',
                    'Annotazioni':'',
                    'row_type':row_type,
                    'origin':origins,
                    'AnnoRif':str(AnnoRif) if bool(AnnoRif) else '0',
                    'NumeroRif':NumeroRif,
                    'sezionale':sezionale,
                    'full_date':full_date
                    }]
                ]
        else:
            multiple_line = []
            AnnoRif, NumeroRif, sezionale, full_date = self.get_anno_numero_rif(stock_move, AnnoRif, NumeroRif, sezionale, full_date)
            IdIva = False
            price_unit = False
            if bool(origin_sale_line_id):
                IdIva = origin_sale_line_id.tax_id.id
            else:
                crma = self.env['return.order.sheet'].search([('number','ilike',origins)])
                if bool(crma):
                    return_order_line_ids = crma.return_order_line_ids.filtered(lambda x: x.product_id == stock_move.product_id)
                    if len(return_order_line_ids) > 1:
                        for return_order_line_id in return_order_line_ids:
                            hts_price = price_unit = return_order_line_id.price if return_order_line_ids else 0.0
                            AnnoRif, NumeroRif, sezionale, full_date = self.get_anno_numero_rif(False, False, False, False, False, return_order_line_id.origin_invoice_id)
                            multiple_line.append((hts_price, price_unit, return_order_line_id.quantity, AnnoRif, NumeroRif, sezionale, full_date))
                    elif len(return_order_line_ids) == 1:
                        hts_price = price_unit = return_order_line_ids.price
                    if bool(crma.partner_id.property_account_position_id):
                        fiscal_position = crma.partner_id.property_account_position_id
                        for tax_id in fiscal_position.tax_ids:
                            if not bool(IdIva):
                                for product_tax_id in stock_move.product_id.taxes_id:
                                    if tax_id.tax_src_id.id == product_tax_id.id:
                                        IdIva = tax_id.tax_dest_id.id
                                        break
            if not multiple_line:
                if not price_unit:
                    price_unit = stock_move.sale_price if bool(stock_move.sale_price) else stock_move.price
                if not hts_price:
                    hts_price = stock_move.sale_price if bool(stock_move.sale_price) else stock_move.price
                multiple_line = [(hts_price, price_unit, quantity, AnnoRif, NumeroRif, sezionale, full_date)]
            
            result = []
            for element_array in multiple_line:
                result.append([0, 0, {
                    'product_id':stock_move.product_id.id,
                    'quantity':element_array[2],
                    'price_unit':element_array[1],
                    'price_htc':element_array[0],
                    'price_subtotal':origin_sale_line_id.price_subtotal if bool(origin_sale_line_id) else ((stock_move.sale_price if bool(stock_move.sale_price) else stock_move.price) * quantity),
                    'sale_order_line_id':origin_sale_line_id.id if bool(origin_sale_line_id) else False,
                    'stock_move_id':stock_move.id,
                    'IdIva':IdIva,
                    'discount':origin_sale_line_id.discount if bool(origin_sale_line_id) else 0.0,
                    'note':'HTS CODE {}'.format(stock_move.product_id.hts_id.code) if bool(stock_move.product_id.hts_id) and bool(stock_move.product_id.hts_id.code) else '',
                    'Annotazioni':stock_move.picking_id.carrier_tracking_ref if bool(stock_move.picking_id.carrier_tracking_ref) else stock_move.picking_id.origin_picking_id.carrier_tracking_ref if bool(stock_move.picking_id.origin_picking_id.carrier_tracking_ref) else '',
                    'row_type':row_type,
                    'origin':origins,
                    'AnnoRif':element_array[3],
                    'NumeroRif':element_array[4],
                    'sezionale':element_array[5],
                    'full_date':element_array[6]
                    }])
            return result
    
    def createLineDocument(self, stock_move, account_os1, quantity, origins, sale_order_line_id=False):
        row_type, hts_price, origin_sale_line_id = self.get_row_type(stock_move, account_os1, sale_order_line_id)
        
        return self.get_vals_line(stock_move, hts_price, origin_sale_line_id, quantity, row_type, origins, sale_order_line_id)
        
    def _createDocuemntOS1(self, list_line, list_stock_picking, list_sale_order, partner_id):
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        vals = {'type':'so',
                'doc_os1_line_ids': list_line,
                'stock_picking_ids':list_stock_picking,
                'sale_order_ids':list_sale_order,
                'partner_id':partner_id.id,
                'account_os1_id':account_os1.id}
        
        return self.env['syd_os1.doc_os1'].create(vals)
    
    def _renderView(self, doc_os1_id):
        [action] = self.env.ref('syd_os1.action_document_os1_after_create').read()
        action['res_id'] = doc_os1_id.id
        return action
    
    def _forStockPicking(self, stock_picking_ids, list_stock_picking, list_line, list_sale_order, origins, sale_order_id=False):
        partner_id = False
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        list_line_dict = {}
        firstSO = False
        if not bool(sale_order_id):
            #Trasferimenti
            partner_id = self.testComplianceStockPicking(stock_picking_ids)
            for stock_picking in stock_picking_ids:
                list_stock_picking.append([4, stock_picking.id])
                for stock_move in stock_picking.move_ids_without_package:
                    if stock_move.picking_id.picking_type_id.code in ['outgoing', 'incoming','internal'] and stock_move.picking_id.state == 'done':
                        if stock_move.quantity_done > 0:
                            origin_sale_line_id = self.getOriginSaleLineId(stock_move)
                            if bool(origin_sale_line_id):
                                if not bool(firstSO):
                                    firstSO = origin_sale_line_id.order_id
                                if origin_sale_line_id.order_id.id not in list_line_dict:
                                    list_line_dict[origin_sale_line_id.order_id.id] = []
                                for element_array in self.createLineDocument(stock_move, account_os1, stock_move.quantity_done, origins):
                                    list_line_dict[origin_sale_line_id.order_id.id].append(element_array)
                                list_sale_order.append([4, origin_sale_line_id.order_id.id])
                            else:
                                if origin_sale_line_id not in list_line_dict:
                                    list_line_dict[origin_sale_line_id] = []
                                for element_array in self.createLineDocument(stock_move, account_os1, stock_move.quantity_done, origins):
                                    list_line_dict[origin_sale_line_id].append(element_array)
                    else:
                        if stock_move.reserved_availability > 0:
                            origin_sale_line_id = self.getOriginSaleLineId(stock_move)
                            if bool(origin_sale_line_id):
                                if not bool(firstSO):
                                    firstSO = origin_sale_line_id.order_id
                                if origin_sale_line_id.order_id.id not in list_line_dict:
                                    list_line_dict[origin_sale_line_id.order_id.id] = []
                                for element_array in self.createLineDocument(stock_move, account_os1, stock_move.reserved_availability, origins):
                                    list_line_dict[origin_sale_line_id.order_id.id].append(element_array)
                                list_sale_order.append([4, origin_sale_line_id.order_id.id])
                            else:
                                if origin_sale_line_id not in list_line_dict:
                                    list_line_dict[origin_sale_line_id] = []
                                for element_array in self.createLineDocument(stock_move, account_os1, stock_move.reserved_availability, origins):
                                    list_line_dict[origin_sale_line_id].append(element_array)
        else:
            partner_id = self.testComplianceStockPicking(False, sale_order_id)
            for sale_order_line_id in sale_order_id.order_line:
                if not bool(sale_order_line_id.display_type):
                    if sale_order_line_id not in list_line_dict:
                        list_line_dict[sale_order_line_id] = []
                    for element_array in self.createLineDocument(False, account_os1, sale_order_line_id.product_uom_qty, origins, sale_order_line_id):
                        list_line_dict[sale_order_line_id].append(element_array)
                    list_sale_order.append([4, sale_order_line_id.order_id.id])
        if len(list_line_dict) == 0:
            raise UserError("Non puoi creare un Documento OS1 con linee vuote, controllare se è già stato creato.")
        new_list_line = []
        for order_id in sorted(list_line_dict):
            for line in list_line_dict[order_id]:
                if line[2]['row_type'] != '3':
                    if bool(firstSO) and not bool(line[2]['sale_order_line_id']):
                        line[2]['second_sale_order_id'] = firstSO.id
                    new_list_line.append(line)
            for line in list_line_dict[order_id]:
                if line[2]['row_type'] == '3':
                    if bool(firstSO) and not bool(line[2]['sale_order_line_id']):
                        line[2]['second_sale_order_id'] = firstSO.id
                    new_list_line.append(line)
        
        return list_stock_picking, list_line + new_list_line, list_sale_order, partner_id