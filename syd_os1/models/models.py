# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tests.common import Form
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

import tempfile
import os
import json
import base64

_logger = logging.getLogger(__name__)
array_row_type = [('1', 'Prodotto'),
                  ('2', 'Servizio/Recupero spese'),
                  ('3', 'Prodotto (descrittivo) [3]'),
                  ('6', 'Annotazioni'),
                  ('7', 'Cessione gratuita'),
                  ('9', 'Rettifica di valore'),
                  ('10', 'Omaggio imponibile'),
                  ('11', 'Omaggio imponibile + Iva'),
                  ('73', 'Prodotto (descrittivo) [73]')]
array_type_doc_os1 = [('0', 'Bolla cliente'),
                      ('1', 'Fattura cliente'),
                      ('2', 'Nota credito'),
                      ('3','Nota debito')]

class DocumentOS1InvoiceDone(models.Model):
    _name = "syd_os1.doc_os1.invoice_done"
    _description = "document OS1 Invoice done"

    name = fields.Char('Name')
    document_number = fields.Char('Document number')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    is_paid = fields.Boolean('Is paid')

    document_os1_id = fields.Many2one('syd_os1.doc_os1', string="DOC OS1")

class ReasonReferenceOS1(models.Model):
    _name = "syd_os1.reason_reference_os1"
    _description = "Reason Reference OS1"

    name = fields.Char('Name')
    code = fields.Char('Code', required=1, size=3)
    description = fields.Char('Description', required=1)

    @api.model
    def create(self, vals):
        reason_reference_os1_id = super(ReasonReferenceOS1, self).create(vals)
        reason_reference_os1_id.name = '[{}] {}'.format(reason_reference_os1_id.code,reason_reference_os1_id.description)
        return reason_reference_os1_id

class DocumentOS1Line(models.Model):
    _name = "syd_os1.doc_os1.line"
    _description = "document OS1 line OS1"

    name = fields.Char('name')
    sequence = fields.Integer(help="Sequence of lines.")
    document_os1_id = fields.Many2one('syd_os1.doc_os1', string="DOC OS1")

    product_id = fields.Many2one('product.product', 'Product')
    quantity = fields.Float('Quantity')
    price_unit = fields.Float('Price unit')
    price_htc = fields.Float('Price HTS')
    price_subtotal = fields.Float('Price subtotal')
    row_type = fields.Selection(array_row_type, string='Row type', default='1')
    partner_destination_id = fields.Many2one('res.partner', 'Cliente')
    IdIva = fields.Many2one('account.tax', string='Iva')
    discount = fields.Float('Discount')
    note = fields.Char('Note')
    Annotazioni = fields.Char('Annotazioni')
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order line')
    sale_order_id = fields.Many2one('sale.order', string="Sale order", related="sale_order_line_id.order_id")
    second_sale_order_id = fields.Many2one('sale.order', string="Sale order second")
    stock_move_id = fields.Many2one('stock.move', 'Sale Move')
    origin = fields.Char('Origins')
    Brand = fields.Many2one('common.product.brand.ept', 'Brand', related="product_id.product_brand_id")
    crma_id = fields.Many2one('return.order.sheet')

    AnnoRif = fields.Char('Anno Riferimento', size=4)
    NumeroRif = fields.Char('Numero Riferimento', size=8)
    sezionale = fields.Char('Sezionale Fattura')
    full_date = fields.Date('Data completa')
    IdCausaleRif = fields.Many2one('syd_os1.reason_reference_os1', 'Causale Riferimento', size=3)

    is_invoiced = fields.Boolean('Is invoiced')

    @api.constrains('AnnoRif')
    def _checkLenIdDestinazione(self):
        try:
            int(self.AnnoRif)
        except Exception as error:
            raise UserError("Anno Riferimento del prodotto: {} non è un numero: {}".format(self.product_id.display_name, self.AnnoRif))

    @api.model
    def create(self, vals):
        doc_os1_line_id = super(DocumentOS1Line, self).create(vals)
        count = self.search_count([('document_os1_id','=',doc_os1_line_id.document_os1_id.id),('id','!=',doc_os1_line_id.id)])
        name = False

        try:
            int(doc_os1_line_id.NumeroRif)
        except Exception as error:
            raise UserError("Numero Riferimento del prodotto: {} non è un numero: {}".format(doc_os1_line_id.product_id.display_name, doc_os1_line_id.NumeroRif))
        if bool(doc_os1_line_id.sale_order_id):
            name = '{}{}{}'.format("{}_".format(doc_os1_line_id.sale_order_id.display_name), '{}_'.format(doc_os1_line_id.stock_move_id.picking_id.display_name) if bool(doc_os1_line_id.stock_move_id) else '', doc_os1_line_id.product_id.display_name)
        else:
            if bool(doc_os1_line_id.origin):
                name = '{}{}{}'.format("{}_".format(doc_os1_line_id.origin), '{}_'.format(doc_os1_line_id.stock_move_id.picking_id.display_name) if bool(doc_os1_line_id.stock_move_id) else '', doc_os1_line_id.product_id.display_name)
            else:
                name = '{}{}{}'.format('', '{}_'.format(doc_os1_line_id.stock_move_id.picking_id.display_name) if bool(doc_os1_line_id.stock_move_id) else '', doc_os1_line_id.product_id.display_name)

        doc_os1_line_id.write({'sequence':count+1,'name':name})
        return doc_os1_line_id

class DocumentOS1(models.Model):
    _name = "syd_os1.doc_os1"
    _description = "Document OS1"
    _inherit = ['mail.thread']


    date_document = fields.Datetime('Date Document',default=fields.Datetime.now)
    account_os1_id = fields.Many2one('syd_os1.os1.account', string="Account OS1")
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    name = fields.Char('Name',default=lambda self: _('New'))
    state = fields.Selection([('draft', 'Draft'),
                              ('validate', 'Validate'),
                              ('done', 'Done'),
                              ('ddt', 'DDT'),
                              ('invoiced', 'Invoiced'),
                              ('paid', 'Paid')], string='State', default='draft', track_visibility='onchange')
    type_doc_os1_internal = fields.Selection([('replacement', 'Sostituzione'),
                              ('ddt', 'DDT'),
                              ('vision_account', 'Conto visione'),
                              ('invoice', 'Fattura'),
                              ('credit_note', 'Nota di credito'),
                              ('proforma', 'Pro forma')], string='internal type OS1', default='invoice')
    type_doc_os1 = fields.Selection(array_type_doc_os1, string='Type OS1', default='1')
    type = fields.Selection([('po', 'Purchase order'),
                              ('so', 'Sale order')], string='Type')
    sale_order_ids = fields.Many2many('sale.order', 'sale_order_document_rel', 'document_os1_id', 'sale_order_id',
                                        string='Sale orders')
    return_order_ids = fields.Many2many('return.order', 'return_order_document_rel', 'document_os1_id', 'return_order_id',
                                        string='Return orders')
    doc_os1_line_ids = fields.One2many('syd_os1.doc_os1.line', 'document_os1_id', string="lines")
    invoice_done_ids = fields.One2many('syd_os1.doc_os1.invoice_done', 'document_os1_id', string="Invoice Done")
    stock_picking_ids = fields.One2many('stock.picking', 'document_os1_id', string="Stock picking")
    stock_picking_many2many_ids = fields.Many2many('stock.picking', 'sp_doc_os1_rel', string="Stock Picking", copy=False)
    stock_picking_internal_ids = fields.One2many('stock.picking', 'document_os1_internal_id', string="Stock internal picking")
    stock_quant_package_ids = fields.One2many('stock.quant.package', 'document_os1_id', string="Stock quant package")
    partner_id = fields.Many2one('res.partner', 'cliente')
    key_returned = fields.Char('Codice documento generato', track_visibility='onchange')
    crma_ids = fields.Many2many('return.order.sheet', 'return_order_sheet_document_rel', 'document_os1_id', 'return_order_sheet_id', string='Commercial return order')
    #Dati testata
    product_category_ids = fields.Many2many('product.category')
    AspettoBeni = fields.Char('Aspetto beni', track_visibility='onchange')
    IdCliente = fields.Char('IdCliente')
    IdDestinazione = fields.Char('IdDestinazione', track_visibility='onchange')
    IdDivisa = fields.Char('IdDivisa')
    SpeseTrasporto = fields.Float('SpeseTrasporto')
    IdAgente1 = fields.Char('IdAgente1')
    IdAgente2 = fields.Char('IdAgente2', default="")
    sconto_t1 = fields.Float('ScontoT1', digits=(12,2))
    IdPagamento = fields.Char('IdPagamento')
    PriceList = fields.Char('PriceList')
    TotNumeroColli = fields.Float('TotNumeroColli')
    TotPesoLordo = fields.Float('TotPesoLordo', digits=(12,2))
    TotPesoNetto = fields.Float('TotPesoNetto', digits=(12,2))
    IdTipoTrasporto = fields.Char('IdTipoTrasporto')
    IdSpedizione1 = fields.Char('IdSpedizione1')
    Brand = fields.Many2one('common.product.brand.ept', 'Brand', compute="_get_brand")
    #Dati Ordine View
    sourceOrder = fields.Char('Source')
    sourceDocument = fields.Char('Source Document')
    fmCodePartner = fields.Char('OS1: Code')
    agent_id = fields.Many2one('res.partner', string="Agente", compute="_setValuesForTheView")
    totalProductsInEuros = fields.Float('Total products in euros', compute="_setValuesForTheView")
    NumberOfPiecesProduced = fields.Integer('Number of pieces produced', compute="_setValuesForTheView")
    Annotazioni = fields.Char('Annotazioni', compute="_setValuesForTheView")
    #Comunicazione con OS1
    flagInvoiceNotImported = fields.Boolean('Fattura con problemi di importazione')
    flagdifferentPayment = fields.Boolean('Flag termini di pagamento diversi')
    differentPayment = fields.Char('Termini di pagamento')
    flagdifferentPaymentCustomer = fields.Boolean('Flag termini di pagamento cliente diversi')
    differentPaymentCustomer = fields.Char('Termini di pagamento cliente')
    flagdifferentPriceList = fields.Boolean('Flag price List diversi')
    differentPriceList = fields.Char('Price List diversi')
    flagInvoiced = fields.Boolean('actually billed')
    flagDdt = fields.Boolean('DDT present')
    messageSendOS1Error = fields.Char('Errore send OS1')
    #Messaggio Creazione
    message_creation = fields.Char('Messaggio di errore creazione')
    #Traccking in PACK e OUT
    carrier_tracking_ref_to_modify = fields.Char('Tracking Reference to modify', track_visibility='onchange')

    def set_to_picking_carrier_tracking_ref(self):
        for picking_id in self.stock_picking_internal_ids:
            picking_id.carrier_tracking_ref = self.carrier_tracking_ref_to_modify

    def getStateOS1(self):
        for doc_os1_id in self:
            doc_os1_id.getDDTState()
            doc_os1_id.getInvoiceState()


    def _setValuesForTheView(self):
        for doc_os1_id in self:
            totalProductsInEuros = 0.0
            NumberOfPiecesProduced = 0
            listAnnotazioni = []
            for line in doc_os1_id.doc_os1_line_ids:
                if line.row_type == '1':
                    totalProductsInEuros += (line.price_unit * line.quantity)
                    NumberOfPiecesProduced += line.quantity
                if line.Annotazioni not in listAnnotazioni and bool(line.Annotazioni):
                    listAnnotazioni.append(line.Annotazioni)
            listSource = []
            listSourceDocument = []
            for so in doc_os1_id.sale_order_ids:
                if so.source_id.display_name not in listSource and bool(so.source_id.display_name):
                    listSource.append(so.source_id.display_name)
                if so.origin not in listSourceDocument and bool(so.origin):
                    listSourceDocument.append(so.origin)

            doc_os1_id.write({'sourceOrder':",".join(str(i) for i in listSource),
                              'sourceDocument':",".join(str(i) for i in listSourceDocument),
                              'totalProductsInEuros':totalProductsInEuros,
                              'NumberOfPiecesProduced':NumberOfPiecesProduced,
                              'Annotazioni':",".join(str(i) for i in listAnnotazioni),
                              'agent_id':doc_os1_id.sale_order_ids[0].salesman_partner_id.id if bool(doc_os1_id.sale_order_ids) else False})

    def getInvoiceState(self):
        for doc_os1_id in self:
            if doc_os1_id.flagInvoiced == False and (doc_os1_id.state in ['done','ddt'] or doc_os1_id.flagInvoiceNotImported == True):
                self.env['syd_os1.os1.account']._getInvoiceState(doc_os1_id.account_os1_id, doc_os1_id)

    def getDDTState(self):
        for doc_os1_id in self:
            if doc_os1_id.state == 'done':
                self.env['syd_os1.os1.account']._getDDTState(doc_os1_id.account_os1_id, doc_os1_id)


    def getInvoice(self):
        for doc_os1_id in self:
            if (doc_os1_id.state in ['invoiced','done','ddt'] or doc_os1_id.flagInvoiceNotImported == True) and doc_os1_id.flagInvoiced == False:
                self.env['syd_os1.os1.account']._getInvoiceCode(doc_os1_id.account_os1_id, doc_os1_id)

    def _cancelInvoice(self):
        for doc_os1 in self:
            if doc_os1.state in ['done','ddt','invoiced']:
                for doc_os1_line in doc_os1.doc_os1_line_ids:
                    doc_os1_line.is_invoiced = False
                doc_os1.invoice_done_ids.unlink()
                doc_os1.write({'state':'done',
                              'flagInvoiced':False,
                              'flagDdt':False,
                              'flagInvoiceNotImported':False})
            else:
                raise UserError("Hai selezionato un documento che non è nello stato 'Done' e 'Invoiced'")

    def cancelInvoice(self):
        for doc_os1 in self:
            if doc_os1.state in ['done','ddt','invoiced']:
                for doc_os1_line in doc_os1.doc_os1_line_ids:
                    doc_os1_line.is_invoiced = False
                for invoice_done_id in doc_os1.invoice_done_ids:
                    for invoice_done_annidate_id in self.env['syd_os1.doc_os1.invoice_done'].search([('invoice_id','=',invoice_done_id.invoice_id.id),('id','!=',invoice_done_id.id)]):
                        invoice_done_annidate_id.document_os1_id._cancelInvoice()
                    invoice_done_id.invoice_id.button_draft()
                    invoice_done_id.invoice_id.with_context(force_delete=True).unlink()
                doc_os1.invoice_done_ids.unlink()
                doc_os1.state = 'done'
            else:
                raise UserError("Hai selezionato un documento che non è nello stato 'Done' e 'Invoiced'")

    @api.constrains('IdDestinazione')
    def _checkLenIdDestinazione(self):
        for doc_os1 in self:
            if bool(doc_os1.IdDestinazione) and len(doc_os1.IdDestinazione) > 4:
                raise UserError("Il valore inserito per IdDestinazione deve essere lungo 4 caratteri ora è lungo:{}".format(len(doc_os1.IdDestinazione)))

    def testProductData(self):
        error_text = ""
        for line in self.doc_os1_line_ids:
            if self.company_id.account_code_os1 == 'milor_account_code':
                milor_account_code = line.product_id.milor_account_code
            else:
                milor_account_code = line.product_id.milor_account_code_id
            if not bool(line.product_id.barcode) or (not bool(milor_account_code) and not bool(line.product_id.is_packaging)) or not bool(line.product_id.default_code):
                barcode = " 'Barcode'" if not bool(line.product_id.barcode) else ''
                milor_account_code_error = " 'Codice Contabilità'" if not bool(milor_account_code) else ''
                default_code = " 'Riferimento interno'" if not bool(line.product_id.default_code) else ''
                error_text = "{}\n {}:{}{}{}".format(error_text, line.product_id.display_name, barcode, milor_account_code_error, default_code)
        if len(error_text) > 0:
            return "Lista articoli non destinati alla vendita o mancano informazioni: {}".format(error_text)
        return False

    def testInfoHeaderInvoice(self):
        fiscal_position = ''
        if not bool(self.partner_id.property_account_position_id):
            fiscal_position = "Il cliente {} non ha una posizione fiscale impostata".format(self.partner_id.display_name)
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        list_type_doc_os1_error = self.setTypeDocOS1()
        type_custom_error, type_picking_error, error_country_partner = self.setTypeDocOS1Internal()
        waitCodeOS1Clienti, waitCodeOS1Destinazione = self.getClientAndDestinazione(account_os1)
        list_order_error, mex_empty_divisa = self.idDivisa()
        self.calcTransportCosts(account_os1)
        waitCodeOS1Agente1, waitCodeOS1Agente2, list_order_agent_error = self.idsAgenti(account_os1)
        self.set_sconti()
        self.idsPagamenti()
        self.numberAndWeightOfPackages()
        list_stocking_error = self.idTransportType()
        list_spedizioni_error = self.forwarder()
        list_aspettibeni_error = self.getAspettoBeni()
        error_text = self.testProductData()

        if bool(waitCodeOS1Clienti) or bool(waitCodeOS1Destinazione) or bool(waitCodeOS1Agente1) or bool(waitCodeOS1Agente2):
            raise UserError("Non puoi creare il documento OS1 perché Alcuni contatti non hanno il codice OS1: {} {} {} {}".format('Cliente: {}'.format(waitCodeOS1Clienti) if bool(waitCodeOS1Clienti) else '', 'Destinazione: {}'.format(waitCodeOS1Destinazione) if bool(waitCodeOS1Destinazione) else '', 'Agente1: {}'.format(waitCodeOS1Agente1) if bool(waitCodeOS1Agente1) else '', 'Agente2: {}'.format(waitCodeOS1Agente2) if bool(waitCodeOS1Agente2) else ''))
        message_error = ''
        if bool(fiscal_position):
            message_error = '{}{}\n'.format(message_error, fiscal_position)
        if bool(list_type_doc_os1_error):
            message_error = '{}Gli Ordini presenti in questo Documento OS1 hanno tipo trasferimento diversi:\n{}\n'.format(message_error, ",".join(str(i) for i in list_type_doc_os1_error))
        if bool(type_custom_error):
            message_error = '{}Gli ordini legati a questo sono di tipo custom differenti:\n{}\n'.format(message_error, ",".join(str(i) for i in type_custom_error))
        if bool(type_picking_error):
            message_error = '{}I trasferimenti presenti in questo Documento OS1 hanno tipi diversi:\n{}\n'.format(message_error, ",".join(str(i) for i in type_picking_error))
        if bool(error_country_partner):
            message_error = '{}{}\n'.format(message_error, error_country_partner)
        if bool(list_order_error):
            message_error = '{}Gli documenti legati a questo Documento OS1 hanno Divise diverse:\n{}\n'.format(message_error, ",".join(str(i) for i in list_order_error))
        if bool(list_order_agent_error):
            message_error = '{}Gli Ordini presenti in questo Documento OS1 hanno Agenti diversi:\n{}\n'.format(message_error, ",".join(str(i) for i in list_order_agent_error))
        if bool(mex_empty_divisa):
            message_error = '{}{}\n'.format(message_error, mex_empty_divisa)
        if bool(list_stocking_error):
            message_error = '{}I Trasferimenti presenti in questo Documento OS1 hanno tipo trasporto diverso:\n{}\n'.format(message_error, ",".join(str(i) for i in list_stocking_error))
        if bool(list_spedizioni_error):
            message_error = '{}I Trasferimenti presenti in questo Documento OS1 hanno tipo spedizioni diverso:\n{}\n'.format(message_error, ",".join(str(i) for i in list_spedizioni_error))
        if bool(list_aspettibeni_error):
            message_error = '{}I trasferimenti presenti in questo Documento OS1 hanno Tipo Pacco diverso:\n{}\n'.format(message_error, ",".join(str(i) for i in list_aspettibeni_error))
        if bool(error_text):
            message_error = '{}{}\n'.format(message_error, error_text)

        if bool(message_error):
            raise UserError(message_error)

    def test_list_error(self, object_1, object_2, list_name):
        if len(list_name) == 0:
            list_name.append(object_1.name)
        list_name.append(object_2.name)
        return list_name

    def write(self, vals):
        res = super(DocumentOS1, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_document' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_document']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'syd_os1.doc_os1', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('syd_os1.doc_os1', sequence_date=seq_date) or _('New')
        doc_os1_id = super(DocumentOS1, self).create(vals)
        doc_os1_id.testInfoHeaderInvoice()
        fmCodePartner = ''
        if bool(doc_os1_id.partner_id.parent_id):
            if bool(doc_os1_id.partner_id.parent_id.fm_code):
                fmCodePartner = doc_os1_id.partner_id.parent_id.fm_code
        else:
            if bool(doc_os1_id.partner_id):
                fmCodePartner = doc_os1_id.partner_id.fm_code

        doc_os1_id.write({'fmCodePartner':fmCodePartner})
        return doc_os1_id

    def unlink(self):
        self.doc_os1_line_ids.unlink()
        for sol in self.sale_order_ids:
            sol.has_doc_os1 = False
        return super(DocumentOS1, self).unlink()

    def setValidate(self):
        self.state = "validate"

    def setDraft(self):
        self.state = "draft"

    def setAnnotazioniCorriere(self):
        list_tipo_trasporto_error = []
        list_corriere_error = []
        is_corriere = False
        for sp in self.stock_picking_internal_ids:
            if not bool(is_corriere):
                is_corriere = sp.carrier_id.os1_code
            if is_corriere != sp.carrier_id.os1_code:
                list_tipo_trasporto_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_tipo_trasporto_error)
        if not bool(is_corriere):
            for sp in self.stock_picking_internal_ids:
                if not bool(is_corriere):
                    is_corriere = sp.carrier_id.os1_code
                if is_corriere != sp.carrier_id.os1_code:
                    list_corriere_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_corriere_error)

        message_error = ''
        if bool(list_tipo_trasporto_error):
            message_error = '{}I Trasferimenti presenti in questo Documento OS1 hanno tipo trasporto diverso:\n{}\n'.format(message_error, ",".join(str(i) for i in list_tipo_trasporto_error))
        if bool(list_corriere_error):
            message_error = '{}I trasferimenti hanno diverso corriere:\n{}\n'.format(message_error, ",".join(str(i) for i in list_corriere_error))
        if bool(message_error):
            raise UserError(message_error)

        if is_corriere in ["1","2"]:
            is_corriere = True
        else:
            is_corriere = False
        if bool(is_corriere):
            for line in self.doc_os1_line_ids:
                line.Annotazioni = '{} {}'.format('TRK', line.Annotazioni)

    def testCountryPartnerTypr(self, partner):
        type = False
        error_mex = ''
        if bool(partner.country_id):
            if partner.country_id.id == self.env['res.country'].search([('code','=','IT')]).id:
                type = 'ddt'
            else:
                type = 'invoice'
        else:
            error_mex = "Il cliente del DOC OS1 {} non ha settata la nazione".format(partner.display_name)

        return type, error_mex

    def setTypeDocOS1Internal(self):
        type_custom_error = []
        type_picking_error = []
        error_country_partner = ''
        type_doc_os1_internal = False
        if bool(self.stock_picking_ids):
            is_vision_account = False
            custom_type = False
            for so in self.sale_order_ids:
                if not bool(custom_type):
                    custom_type = so.custom_type
                if custom_type != so.custom_type:
                    type_custom_error = self.test_list_error(self.sale_order_ids[0], so, type_custom_error)
            if custom_type == 'vision_account':
                is_vision_account = True
            for sp in self.stock_picking_ids:
                if bool(is_vision_account):
                    type = 'vision_account'
                elif bool(sp.group_id.crma_id if bool(sp.group_id) else False) or bool(sp.rma_id):
                    cro = sp.group_id.crma_id or sp.rma_id
                    if cro.return_type == 'replacement':
                        type = 'replacement'
                    else:
                        type = 'credit_note'
                elif sp.picking_type_id.code == 'incoming':
                    type = 'credit_note'
                elif bool(sp.origin_sale_id.proFormaType if bool(sp.origin_sale_id) else False):
                    type = 'proforma'
                else:
                    if bool(self.partner_id.parent_id):
                        type, error_country_partner = self.testCountryPartnerTypr(self.partner_id.parent_id)
                    else:
                        type, error_country_partner = self.testCountryPartnerTypr(self.partner_id)
                if not bool(type_doc_os1_internal):
                    type_doc_os1_internal = type
                if type != type_doc_os1_internal:
                    type_picking_error = self.test_list_error(self.stock_picking_ids[0], sp, type_picking_error)
        else:
            for so in self.sale_order_ids:
                if so.proFormaType:
                    type_doc_os1_internal = 'proforma'
                else:
                    type_doc_os1_internal = False
                    break
        if not bool(type_doc_os1_internal):
            type_doc_os1_internal = 'invoice'

        self.type_doc_os1_internal = type_doc_os1_internal

        return type_custom_error, type_picking_error, error_country_partner

    def setTypeDocOS1(self):
        list_type_doc_os1_error = []
        type_doc_os1 = False
        for sp in self.stock_picking_ids:
            if sp.group_id.crma_id.return_type == 'replacement':
                type = '1'
            elif sp.picking_type_id.code == 'outgoing':
                type = '1'
            elif sp.picking_type_id.code == 'incoming':
                type = '2'
            elif sp.picking_type_id.code == 'internal' :
                type = '1'
            else:
                type = '3'
            if not bool(type_doc_os1):
                type_doc_os1 = type
            if type != type_doc_os1:
                list_type_doc_os1_error = self.test_list_error(self.stock_picking_ids[0], sp, list_type_doc_os1_error)
        if not bool(type_doc_os1):
            type_doc_os1 = '1'
        self.type_doc_os1 = type_doc_os1
        return list_type_doc_os1_error

    def getClientAndDestinazione(self, account_os1):
        is_destination = False
        if bool(self.partner_id.parent_id):
            #è un indirizzo di destinazione
            if not bool(self.partner_id.parent_id.fm_id):
                IdCliente = '00000000'
            else:
                IdCliente = self.partner_id.parent_id.fm_id.zfill(8)
            if not bool(self.partner_id.fm_subtype_id):
                IdDestinazione = '0000'
            else:
                IdDestinazione = self.partner_id.fm_subtype_id.zfill(4)
            nameCustomer = self.partner_id.parent_id.display_name
            nameDestination = self.partner_id.display_name
            is_destination = True
        else:
            if not bool(self.partner_id.fm_id):
                IdCliente = '00000000'
            else:
                IdCliente = self.partner_id.fm_id.zfill(8)
            IdDestinazione = '0000'
            nameCustomer = self.partner_id.display_name
            nameDestination = self.partner_id.display_name
            #è un cliente

        if not bool(IdDestinazione):
            account_os1.createTemporaryCustomers(self.partner_id)
            return nameCustomer if not bool(IdCliente) else False, nameDestination

        if not bool(IdCliente) or IdCliente == '00000000':
            if is_destination:
                account_os1.createTemporaryCustomers(self.partner_id.parent_id)
                return nameCustomer, False
            else:
                account_os1.createTemporaryCustomers(self.partner_id)
                return nameCustomer, False

        self.IdCliente = IdCliente
        self.IdDestinazione = IdDestinazione

        return False, False

    def idDivisa(self):
        list_order_error = []
        IdDivisa = False
        for so in self.sale_order_ids:
            if not bool(so.currency_id.os1_code):
                continue
            if not bool(IdDivisa):
                IdDivisa = so.currency_id.os1_code.zfill(3)
            if IdDivisa != so.currency_id.os1_code.zfill(3):
                list_order_error = self.test_list_error(self.sale_order_ids[0], so, list_order_error)
        if not bool(IdDivisa):
            for sp in self.stock_picking_ids:
                if not bool(sp.currency_id.os1_code):
                    continue
                if not bool(IdDivisa):
                    IdDivisa = sp.currency_id.os1_code.zfill(3)
                if IdDivisa != sp.currency_id.os1_code.zfill(3):
                    list_order_error = self.test_list_error(self.stock_picking_ids[0], sp, list_order_error)
        if not bool(IdDivisa):
            for spi in self.stock_picking_internal_ids:
                if not bool(spi.currency_id.os1_code):
                    continue
                if not bool(IdDivisa):
                    IdDivisa = spi.currency_id.os1_code.zfill(3)
                if IdDivisa != spi.currency_id.os1_code.zfill(3):
                    list_order_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_order_error)
        mex_empty_divisa = ''
        if not bool(IdDivisa):
            mex_empty_divisa = "La divisa non ha il codice OS1"
        if not bool(IdDivisa):
            IdDivisa = '000'

        self.IdDivisa = IdDivisa

        return list_order_error, mex_empty_divisa

    def calcTransportCosts(self, account_os1):
        tot = 0.0
        if len(self.sale_order_ids) == 0:
            for line in self.doc_os1_line_ids.filtered(lambda dol: dol.product_id.categ_id.id == account_os1.categ_id.id):
                tot += (line.price_unit * line.quantity)
        else:
            for so in self.sale_order_ids:
                for sol in so.order_line:
                    if sol.product_id.categ_id.id == self.account_os1_id.categ_id.id:
                        tot += abs(sol.price_subtotal)
        self.SpeseTrasporto = tot

    def idsAgenti(self, account_os1):#guardare ogni SO e vedere se sono tutti uguali senò errore
        list_order_agent_error = []
        IdAgente1 = False

        salesman_id = self.env['res.partner']

        for so in self.sale_order_ids:
            if bool(so.partner_id.salesman_partner_id):
                if not bool(so.partner_id.salesman_partner_id.fm_id):
                    account_os1.createTemporaryCustomers(so.partner_id.salesman_partner_id)
                    return so.partner_id.salesman_partner_id.display_name if bool(not IdAgente1) else IdAgente1, False, False
                else:
                    IdAgente1 = so.partner_id.salesman_partner_id.fm_id.zfill(3)
                    break

        if not bool(IdAgente1):
            IdAgente1 = '035'
        if self.crma_ids and self.partner_id.salesman_partner_id.fm_id:
            IdAgente1 = self.partner_id.salesman_partner_id.fm_id

        self.IdAgente1 = IdAgente1

        return False, False, list_order_agent_error

    def set_sconti(self):
        tot_discount = 0.0
        for so in self.sale_order_ids:
            for sol in so.order_line:
                if sol.product_id.categ_id.id == self.account_os1_id.categ_product_discount_id.id:
                    tot_discount += abs(sol.price_subtotal)
        tot_discount = 0.0
        self.sconto_t1 = tot_discount

    def idsPagamenti(self):
        IdPagamento = False
        IdPagamentoCustomer = False
        PriceList = False

        arryaPagamento = []
        arryaPagamentoCustomer = []
        arryaPriceList = []

        for so in self.sale_order_ids:
            if bool(so.payment_term_id.os1_code):
                if not bool(IdPagamento):
                    IdPagamento = so.payment_term_id.os1_code.zfill(3)
                if IdPagamento != so.payment_term_id.os1_code.zfill(3):
                    self.flagdifferentPayment = True
                namePagamento = '{}({})'.format(so.payment_term_id.display_name, so.payment_term_id.os1_code.zfill(3))
                if namePagamento not in arryaPagamento:
                    arryaPagamento.append(namePagamento)

            if bool(so.partner_payment_term_id.os1_code):
                if not bool(IdPagamentoCustomer):
                    IdPagamentoCustomer = so.partner_payment_term_id.os1_code.zfill(3)
                if IdPagamentoCustomer != so.partner_payment_term_id.os1_code.zfill(3):
                    self.flagdifferentPaymentCustomer = True
                namePagamento = '{}({})'.format(so.partner_payment_term_id.display_name, so.partner_payment_term_id.os1_code.zfill(3))
                if namePagamento not in arryaPagamentoCustomer:
                    arryaPagamentoCustomer.append(namePagamento)
            if bool(so.pricelist_id.pepperi_name):
                if not bool(PriceList):
                    PriceList = so.pricelist_id.pepperi_name
                if PriceList != so.pricelist_id.pepperi_name:
                    self.flagdifferentPriceList = True
                namePriceList = so.pricelist_id.pepperi_name
                if namePriceList not in arryaPriceList:
                    arryaPriceList.append(namePriceList)

        if not bool(IdPagamento):
            if self.type_doc_os1 == "2":
                IdPagamento = '001'
        if not bool(IdPagamento):
            if bool(self.partner_id.property_payment_term_id):
                IdPagamento = self.partner_id.property_payment_term_id.os1_code.zfill(3)
        if not bool(IdPagamento):
            IdPagamento = '000'
        if self.crma_ids:
            IdPagamento = '001'

        if len(arryaPagamento) > 0:
            self.differentPayment = ",".join(str(i) for i in arryaPagamento)
        if len(arryaPagamentoCustomer) > 0:
            self.differentPaymentCustomer = ",".join(str(i) for i in arryaPagamentoCustomer)
        if len(arryaPriceList) > 1:
            self.differentPriceList = ",".join(str(i) for i in arryaPriceList)

        self.IdPagamento = IdPagamento
        self.PriceList = PriceList

    def numberAndWeightOfPackages(self):
        TotNumeroColli, TotPesoLordo, TotPesoNetto = 0.0, 0.0, 0.0
        list_package = []
        for package in self.stock_picking_ids.move_line_ids.mapped('result_package_id'):
            if package.id not in list_package:
                list_package.append(package.id)
                TotNumeroColli += 1.0
                TotPesoLordo += (package.shipping_weight * 1000)
        for line in self.doc_os1_line_ids:
            TotPesoNetto += (line.product_id.weight_gr * line.quantity)

        self.TotNumeroColli = TotNumeroColli
        self.TotPesoLordo = TotPesoLordo
        self.TotPesoNetto = TotPesoNetto

    def idTransportType(self):
        list_stocking_error = []
        IdTipoTrasporto = False
        for sp in self.stock_picking_ids:
            if not bool(sp.carrier_id.os1_code):
                    continue
            if not bool(IdTipoTrasporto):
                IdTipoTrasporto = sp.carrier_id.os1_code.zfill(2)
            if IdTipoTrasporto != sp.carrier_id.os1_code.zfill(2):
                list_stocking_error = self.test_list_error(self.stock_picking_ids[0], sp, list_stocking_error)

        if not bool(IdTipoTrasporto):
            for sp in self.stock_picking_internal_ids:
                if not bool(sp.carrier_id.os1_code):
                    continue
                if not bool(IdTipoTrasporto):
                    IdTipoTrasporto = sp.carrier_id.os1_code.zfill(2)
                if IdTipoTrasporto != sp.carrier_id.os1_code.zfill(2):
                    list_stocking_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_stocking_error)

        if not bool(IdTipoTrasporto):
            IdTipoTrasporto = '00'

        self.IdTipoTrasporto = IdTipoTrasporto

        return list_stocking_error

    def forwarder(self):
        list_spedizioni_error = []
        IdSpedizione1 = False
        for sp in self.stock_picking_ids:
            if not bool(sp.delivery_partner_id.fm_id):
                    continue
            if not bool(IdSpedizione1):
                    IdSpedizione1 = sp.delivery_partner_id.fm_id
            if IdSpedizione1 != sp.delivery_partner_id.fm_id:
                list_spedizioni_error = self.test_list_error(self.stock_picking_ids[0], sp, list_spedizioni_error)
        if not bool(IdSpedizione1):
            for sp in self.stock_picking_internal_ids:
                if not bool(sp.delivery_partner_id.fm_id):
                    continue
                if not bool(IdSpedizione1):
                    IdSpedizione1 = sp.delivery_partner_id.fm_id
                if IdSpedizione1 != sp.delivery_partner_id.fm_id:
                    list_spedizioni_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_spedizioni_error)
        if not bool(IdSpedizione1):
            IdSpedizione1 = '000'

        self.IdSpedizione1 = IdSpedizione1

        return list_spedizioni_error

    def getAspettoBeni(self):
        list_aspettibeni_error = []
        AspettoBeni = False
        for sp in self.stock_picking_ids:
            if bool(sp.carrier_id.dhl_default_packaging_id.shipper_package_code):
                if not bool(AspettoBeni):
                    AspettoBeni = sp.carrier_id.dhl_default_packaging_id.shipper_package_code
                if AspettoBeni != sp.carrier_id.dhl_default_packaging_id.shipper_package_code:
                    list_aspettibeni_error = self.test_list_error(self.stock_picking_ids[0], sp, list_aspettibeni_error)
            if bool(sp.carrier_id.ups_default_packaging_id.shipper_package_code):
                if not bool(AspettoBeni):
                    AspettoBeni = sp.carrier_id.ups_default_packaging_id.shipper_package_code
                if AspettoBeni != sp.carrier_id.ups_default_packaging_id.shipper_package_code:
                    list_aspettibeni_error = self.test_list_error(self.stock_picking_ids[0], sp, list_aspettibeni_error)
        if not bool(AspettoBeni):
            for sp in self.stock_picking_internal_ids:
                if bool(sp.carrier_id.dhl_default_packaging_id.shipper_package_code):
                    if not bool(AspettoBeni):
                        AspettoBeni = sp.carrier_id.dhl_default_packaging_id.shipper_package_code
                    if AspettoBeni != sp.carrier_id.dhl_default_packaging_id.shipper_package_code:
                        list_aspettibeni_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_aspettibeni_error)
                if bool(sp.carrier_id.ups_default_packaging_id.shipper_package_code):
                    if not bool(AspettoBeni):
                        AspettoBeni = sp.carrier_id.ups_default_packaging_id.shipper_package_code
                    if AspettoBeni != sp.carrier_id.ups_default_packaging_id.shipper_package_code:
                        list_aspettibeni_error = self.test_list_error(self.stock_picking_internal_ids[0], sp, list_aspettibeni_error)

        self.AspettoBeni = AspettoBeni if bool(AspettoBeni) else ''

        return list_aspettibeni_error

    def _get_brand(self):
        for doc_os1_id in self:
            line_doc_os1_with_brand = doc_os1_id.doc_os1_line_ids.filtered(lambda line_doc_os1_id: bool(line_doc_os1_id.product_id.product_brand_id))
            if bool(line_doc_os1_with_brand):
                doc_os1_id.Brand = line_doc_os1_with_brand[0].product_id.product_brand_id
            else:
                doc_os1_id.Brand = False

    def forceDDT(self):
        for doc_os1_id in self:
            if doc_os1_id.state == 'done':
                doc_os1_id.write({'state':'ddt',
                                  'flagDdt':True})

    def forceInvoice(self):
        for doc_os1_id in self:
            if doc_os1_id.state in ['done','ddt']:
                doc_os1_id.write({'state':'invoiced',
                                  'flagInvoiced':True})

    def _setDone(self, key):
        self.write({'key_returned':key,'state':'done','messageSendOS1Error':''})

    def forceDone(self):
        if len(self) > 1:
            raise UserError('You can only force invoice to a DOC OS1')

        [action] = self.env.ref('syd_os1.action_wizard_force_done').read()
        action['context']= {'default_doc_os1_id':self.id}
        return action

    def get_list_line(self, list_line):
        for line in self.doc_os1_line_ids:
            if bool(line.sale_order_id):
                date_order = line.sale_order_id.date_order
                RiferimentiPO = line.sale_order_id.display_name[:50]
            elif bool(line.second_sale_order_id):
                date_order = line.second_sale_order_id.date_order
                RiferimentiPO = line.second_sale_order_id.display_name[:50]
            elif bool(line.crma_id):
                date_order = line.crma_id.create_date
                RiferimentiPO = line.crma_id.display_name[:50]
            else:
                date_order = datetime.now()
                RiferimentiPO = 'FALSE'

            IdIva = '000'
            if bool(line.IdIva.os1_code):
                IdIva = str(line.IdIva.os1_code).zfill(3)
                if bool(self.partner_id.country_id):
                    if self.partner_id.country_id.id == self.env['res.country'].search(
                            [('code', '=', 'IT')]).id and (line.row_type in ['10', '11']):
                        IdIva = str('{}{}'.format('I', line.IdIva.os1_code)).zfill(3)
            elif self.stock_picking_internal_ids:
                if line.stock_move_id:
                    if line.stock_move_id.picking_id.origin and line.stock_move_id.picking_id.origin[:4] == 'CRMA':
                        date_line = False
                        crma_id = self.env['return.order.sheet'].search(
                            [('number', '=', line.stock_move_id.picking_id.origin)], limit=1)
                        if crma_id.partner_id.country_id.code == 'IT':
                            for crma_line in crma_id.return_order_line_ids:
                                if crma_line.product_id == line.product_id:
                                    date_line = crma_line.origin_invoice_id.invoice_date
                        else:
                            if crma_id.partner_id.property_account_position_id:
                                for tax in crma_id.partner_id.property_account_position_id.tax_ids:
                                    if line.product_id.taxes_id == tax.tax_src_id:
                                        IdIva = str(int(tax.tax_dest_id.amount)).zfill(3)
                                if IdIva == '000':
                                    IdIva = str(int(line.product_id.taxes_id.amount)).zfill(3)
                        if date_line:
                            if date_line >= (datetime.today().date() - timedelta(days=365)):
                                IdIva = '022'
                            else:
                                IdIva = '066'
            if self.crma_ids:
                date_line = False
                for crma_id in self.crma_ids:
                    if crma_id.id == line.crma_id.id and crma_id.partner_id.country_id.code == 'IT':
                        for crma_line in crma_id.return_order_line_ids:
                            if crma_line.product_id == line.product_id:
                                date_line = crma_line.origin_invoice_id.invoice_date
                    elif crma_id.id == line.crma_id.id and crma_id.partner_id.country_id.code != 'IT':
                        if crma_id.partner_id.property_account_position_id:
                            for tax in crma_id.partner_id.property_account_position_id.tax_ids:
                                if line.product_id.taxes_id == tax.tax_src_id:
                                    IdIva = str(int(tax.tax_dest_id.amount)).zfill(3)
                            if IdIva == '000':
                                IdIva = str(int(line.product_id.taxes_id.amount)).zfill(3)
                if date_line:
                    if date_line >= (datetime.today().date() - timedelta(days=365)):
                        IdIva = '022'
                    else:
                        IdIva = '066'
                    # if self.crma_ids[0].partner_id.country_id.code == 'IT':
                    #     invoice_date = self.crma_ids[0].return_order_line_ids[0].origin_invoice_id.invoice_date
                    #     if invoice_date >= (self.crma_ids[0].create_date.date() - relativedelta(years=1)) and invoice_date <= self.crma_ids[0].create_date.date():
                    #         IdIva = '022'
                    #     else:
                    #         IdIva = '066'

            if ")" in RiferimentiPO or "(" in RiferimentiPO:
                RiferimentiPO = RiferimentiPO[:len(RiferimentiPO)-1]
                if bool(line.sale_order_id.client_order_ref):
                    if "(" in RiferimentiPO:
                        RiferimentiPO = "{}, {})".format(RiferimentiPO, line.sale_order_id.client_order_ref)
                else:
                    RiferimentiPO = "{})".format(RiferimentiPO)

            str_note = 'NULL'
            if line.note:
                str_note = line.note
                if self.crma_ids:
                    str_note = '{} | {}'.format(line.note, 'Rif: {}/{} Invoice Date: {}'.format(line.NumeroRif, line.sezionale, line.full_date))

            if self.company_id.account_code_os1 == 'milor_account_code':
                id_product = line.product_id.milor_account_code if bool(line.product_id.milor_account_code) else ''
            else:
                id_product = line.product_id.milor_account_code_id.name if bool(line.product_id.milor_account_code_id) else ''

            data = {'IdCliente':self.IdCliente,#Testo(8)
                    'IdDestinazione':int(self.IdDestinazione),#intero(4)
                    'FlTipoDoc':int(self.type_doc_os1),#intero(2)
                    'IdDivisa':self.IdDivisa,#Testo(3)
                    'SpeseTrasporto':self.SpeseTrasporto,#Decimale variabile (14)
                    'SpeseImballo':0.0,#Decimale variabile (14)
                    'SpeseVarie':0.0,#Decimale variabile (14)
                    'IdAgente1':self.IdAgente1,#Testo (5)
                    'IdAgente2':self.IdAgente2,#Testo (5)
                    'ScontoT1':self.sconto_t1,#Decimale (14)
                    'ScontoT2':0.0,#Decimale (14)
                    'IdPagamento':self.IdPagamento,#Testo (3)
                    'TotNumeroColli':self.TotNumeroColli,#Decimale (14)
                    'TotPesoLordo':self.TotPesoLordo,#Decimale (14)
                    'TotPesoNetto':self.TotPesoNetto,#Decimale (14)
                    'IdTipoTrasporto':int(self.IdTipoTrasporto),#Intero (2)
                    'IdSpedizione1':self.IdSpedizione1,#Testo (3)
                    'IdSpedizione2':"",#Testo (3)
                    'IdPorto':"1",#Testo (3)
                    'AspettoBeni':self.AspettoBeni[:60] if bool(self.AspettoBeni) else '',#Testo (60)
                    'Annotazioni':line.Annotazioni[:60] if bool(line.Annotazioni) else '',#Testo (60)
                    'NumOrdine':line.sequence,#Intero Lungo (8)
                    'TipoRigo':int(line.row_type),#Intero (4)
                    'IdIva':IdIva,#Testo (3)
                    'IdProdotto':id_product,#Testo (22)
                    'RiferimentiPO':RiferimentiPO,#Testo (50)
                    # NexApp nuova formattazione data
                    # 'DataPO':"{}-{}-{}T{}:{}:{}.{}+{}:{}".format(date_order.year,date_order.month,date_order.day,date_order.hour,date_order.minute,date_order.second,date_order.microsecond,'01','00'),#Data (8)
                    'DataPO': "{}-{}-{}T{}:{}:{}.{}+{}:{}".format(str(date_order.year).zfill(4),
                                                            str(date_order.month).zfill(2),
                                                            str(date_order.day).zfill(2),
                                                            str(date_order.hour).zfill(2),
                                                            str(date_order.minute).zfill(2),
                                                            str(date_order.second).zfill(2),
                                                            str(date_order.microsecond).zfill(3),
                                                            '01', '00'),#Data (8)
                    'NumeroDistintaFM':self.name,#Testo (30)
                    'Quantita':line.quantity,#Decimale Variabile (14)
                    'Prezzo':line.price_unit,#Decimale Variabile (14)
                    'ValoreHts':line.price_htc,
                    'Sconto1':line.discount,#Decimale (5)
                    'Sconto2':0.0,#Decimale (5)
                    'Sconto3':0.0,#Decimale (5)
                    'IdProdottoBase':line.product_id.default_code,#Testo (30)
                    'Note':str_note,#Memo (8)
                    'PesoLordo':(line.product_id.weight_gr * line.quantity),#Decimale (14)
                    'PesoNetto':(line.product_id.weight_gr * line.quantity),#Decimale (14)
                    'DsProdotto':line.product_id.name if bool(line.product_id.name) else '',#Testo (60)
                    'EanCode':line.product_id.barcode if bool(line.product_id.barcode) else '',#Testo (22)
                    'AnnoRif':int(line.AnnoRif),#Intero (4)
                    'NumeroRif':int(line.NumeroRif),#Intero (8)
                    'IdCausaleRif':line.IdCausaleRif.code if bool(line.IdCausaleRif) else ''}#Testo (3)
            list_line.append(data)
        return list_line

    def create_file_json(self, list_line=False):
        for doc_os1_id in self:
            if not bool(list_line):
                list_line = doc_os1_id.get_list_line([])
            attachement_ids = self.env['ir.attachment'].search([('res_model','=','syd_os1.doc_os1'),
                                                                ('res_id','=',doc_os1_id.id),
                                                                ('res_name','=','DocumentOS1')])
            filename = '{}_Distinta_{}.json'.format(doc_os1_id.name, len(attachement_ids)).replace(' ', '_')
            pathFile = os.path.join(tempfile.gettempdir(), filename)
            with open(pathFile, 'w') as fileWrite:
                fileWrite.write(json.dumps(list_line))
            with open(pathFile, 'rb') as fileRead:
                datas = fileRead.read()
            attachement = self.env['ir.attachment'].create({'name': filename,
                                                            'datas': base64.b64encode(datas),
                                                            'type': 'binary',
                                                            'res_model':'syd_os1.doc_os1',
                                                            'res_id':doc_os1_id.id,
                                                            'res_name':'DocumentOS1',
                                                            'mimetype': 'application/json'})

            os.remove(pathFile)
            list_line = False

    def setDone(self):
        #comunica a OS1 i Document OS1 usando il servizio http://127.0.0.1:8080/rest/idea/import/ImportDocumento riga per riga usando come punto di riferimento l'ordine
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        list_line = []
        hundreds = 1
        list_line_product = {hundreds:[]}
        #Creare i prodotti su OS1
        try:
            count = 0
            for line in self.doc_os1_line_ids:
                if bool(line.product_id.is_packaging):
                    continue
                else:
                    EanCode = line.product_id.barcode#Barcode
                    IdProdotto = line.product_id.default_code #Internal Reference
                    IdProdottoBase = line.product_id.milor_account_code if self.company_id.account_code_os1 == 'milor_account_code' else  line.product_id.milor_account_code_id.name#Codice contabilità
                data_product = {'EanCode':EanCode,
                                'IdProdotto':IdProdotto,
                                'DsProdotto':line.product_id.name,
                                'IdProdottoBase':IdProdottoBase,
                                'PesoLordo':line.product_id.weight_gr,
                                'PesoNetto':line.product_id.weight_gr}
                list_line_product[hundreds].append(data_product)
                count += 1
                if count % 100 == 0:
                    hundreds += 1
                    list_line_product[hundreds] = []
        except Exception as error:
            vals = {'type':'other',
                    'message_error':error,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':account_os1.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            self.messageSendOS1Error = error
            self._cr.commit()
            raise UserError("Errore: {}".format(error))

        #Crea File Json
#         paths = []
#         for hundreds in list_line_product:
#             pathFile = os.path.join(tempfile.gettempdir(), '{}_{}.json'.format(self.name, hundreds).replace(' ', '_'))
#             with open(pathFile, 'w') as fileWrite:
#                 fileWrite.write(json.dumps(list_line_product[hundreds]))
#             paths.append(pathFile)
#         for path in paths:
#             os.remove(path)
        #Fine crea file json

        for hundreds in list_line_product:
            key, error = account_os1.createProductOS1(list_line_product[hundreds])
            if bool(error):
                vals = {'type':'other',
                        'message_error':error,
                        'model':self._name,
                        'res_id':self.id,
                        'os1_account_id':account_os1.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
                self.messageSendOS1Error = 'Errore in invio Prodotti a OS1'
                self._cr.commit()
                raise UserError("errore inserimento prodotti: {}".format(error))

        #Creare le righe di distinta
        try:
            list_line = self.get_list_line(list_line)
        except Exception as error:
            vals = {'type':'other',
                    'message_error':error,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':account_os1.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            self.messageSendOS1Error = error
            self._cr.commit()
            raise UserError("Errore: {}".format(error))

        self.create_file_json(list_line)

        key, error = account_os1.createDocumentOS1Line(list_line)
        if bool(error):
            vals = {'type':'other',
                    'message_error':error,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':account_os1.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            self.messageSendOS1Error = "Errore in inserimento Distinta: {}".format(error)
            self._cr.commit()
            raise UserError("errore inserimento Distinta {} con id {}: {}".format(self.name, self.id, error))
        self.write({'key_returned':key,
                    'state':'done',
                    'messageSendOS1Error':''})

    def testResponseOS1Invoice(self, response, os1_account):
        os1_code = False
        error_client = False
        if bool(self.partner_id.parent_id):
            os1_code = self.partner_id.parent_id.fm_id.zfill(8)
        else:
            os1_code = self.partner_id.fm_id.zfill(8)
        for invoice in response:
            if os1_code != invoice['IdCliente']:
                error_client = True
                break
        if error_client:
            vals = {'type':'invoice',
                    'message_error':'multi client after request for DOC OS1: {}'.format(self.id),
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':os1_account.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            return False
        else:
            vals = {'type':'invoice',
                    'message_error':'Per DOC OS1: {} con key: {} si ha response: {}'.format(self.display_name, self.key_returned, response),
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':os1_account.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            return True

    def invoiceIsDone(self, name, document_number):
        for invoice_done_id in self.invoice_done_ids:
            if invoice_done_id.name == str(name) and invoice_done_id.document_number == document_number:
                return True
        return False

    def getTypeDocInvoice(self):
        if self.type_doc_os1 == '2':
            return 'in_invoice'
        else:
            return 'out_invoice'

    def forceCreateInvoice(self):
        [action] = self.env.ref('syd_os1.action_wizard_import_invoice').read()

        action['context']= {'default_doc_os1_ids':[[6,False,self.ids]]}

        return action

    def _getTypeRow(self, doc_os1_line):
        DsTipoRigo = False
        for type_rigo in array_row_type:
            if type_rigo[0] == doc_os1_line.row_type:
                DsTipoRigo = type_rigo[1]
        return DsTipoRigo

    def _forceCreateInvoice(self, KTestaDoc, NumDocumento, DataDocumento):
        state = True
        IdDivisa = self[0].IdDivisa
        for doc_os1 in self:
            if doc_os1.state != 'invoiced' and doc_os1.flagInvoiced:
                state = False
                break

        partner = False
        for doc_os1 in self:
            if not bool(partner):
                partner = doc_os1.partner_id
            if partner.id != doc_os1.partner_id.id:
                raise UserError('The selected OS1 DOCs have different customers')

        if state:
            dictRighe = []
            for doc_os1 in self:
                for doc_os1_line in doc_os1.doc_os1_line_ids:
                    if not doc_os1_line.is_invoiced:
                        DsTipoRigo = doc_os1._getTypeRow(doc_os1_line)
                        dictRighe.append({'DsCodProdotto':doc_os1_line.product_id.default_code,
                                          'IdKeyFM':doc_os1.key_returned,
                                          'DsTipoRigo':DsTipoRigo,
                                          'TipoRigo':doc_os1_line.row_type,
                                          'Quantita':doc_os1_line.quantity})

            invoice = {'KTestaDoc':KTestaDoc,
                       'NumDocumento':NumDocumento,
                       'IdDivisa':IdDivisa,
                       'DataDocumento':str(DataDocumento),
                       'Righe':dictRighe}

            for doc_os1 in self:
                doc_os1._createInvoice(invoice)
                doc_os1.state = 'invoiced'

    def _createInvoice(self, invoice):
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        list_invoice_origin = []
        invoice_done_id = self.env['syd_os1.doc_os1.invoice_done'].search([('document_number','=',invoice['NumDocumento'])])
        if bool(invoice_done_id):
            new_invoice_done_id = invoice_done_id[0].copy()
            new_invoice_done_id.document_os1_id = self.id
            self.write({'flagInvoiceNotImported':False,
                        'flagInvoiced':True})
        else:
            sale_order_names = []
            errore_in_line = False
            with Form(self.env['account.move'].with_context(default_type=self.getTypeDocInvoice())) as invoice_form:
                #partner_id
                invoice_form.partner_id = self.partner_id.commercial_partner_id
                #partner_id
                invoice_form.partner_shipping_id = self.partner_id
                #currency_id
                invoice_form.currency_id = self.env['res.currency'].search([('os1_code','=',str(int(invoice['IdDivisa'])))])
                #invoice_date
                invoice_form.invoice_date = invoice['DataDocumento'][:10]
                #TODO: invoice_partner_bank_id
                if bool(account_os1.journal_id):
                    invoice_form.journal_id = account_os1.journal_id
                #linee
                lines_doc_os1 = {}
                for line in invoice['Righe']:
                    if bool(line['IdKeyFM']):
                        if line['IdKeyFM'] not in lines_doc_os1:
                            lines_doc_os1[line['IdKeyFM']] = []
                        lines_doc_os1[line['IdKeyFM']].append(line)

                for IdKeyFM in lines_doc_os1:
                    doc_os1_id = self.search([('key_returned','=',IdKeyFM)])
                    list_invoice_origin.append(doc_os1_id.display_name)
                    for line in lines_doc_os1[IdKeyFM]:
                        if line['IdKeyFM'] == doc_os1_id.key_returned:
                            for sale_order_id in doc_os1_id.sale_order_ids:
                                if sale_order_id.display_name == line['RiferimentiPO']:
                                    if line['RiferimentiPO'] not in sale_order_names:
                                        sale_order_names.append(line['RiferimentiPO'])
                            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                                if not bool(account_os1.jump_doc_os1_line):
                                    doc_os1_line = self.env['syd_os1.doc_os1.line'].search([('document_os1_id','=',doc_os1_id.id),('is_invoiced','=',False)], limit=1)
                                    if line['DsTipoRigo'] != 'Annotazioni' and (doc_os1_line.quantity != line['Quantita'] or doc_os1_line.row_type != str(line['TipoRigo'])):
                                        self.env['ir.logging'].create({'name':'Create DOC OS1',
                                                                       'func':'Create DOC OS1',
                                                                       'line':1,
                                                                       'message':'Linee non conformi',
                                                                       'path':'Create DOC OS1',
                                                                       'type':'server'})
                                        errore_in_line = True
                                    invoice_line_form.product_id = doc_os1_line.product_id
                                    invoice_line_form.price_unit = doc_os1_line.price_unit
                                    invoice_line_form.name = str(doc_os1_line.id)
                                    invoice_line_form.quantity = doc_os1_line.quantity

                                    doc_os1_line.is_invoiced = True
                                else:
                                    product_id = self.env['product.product']
                                    if bool(line['IdProdotto']) and bool(line['DsCodProdotto']):
                                        if account_os1.company_id.account_code_os1 == 'milor_account_code':
                                            product_id = self.env['product.product'].search(
                                                [('milor_account_code', '=', line['IdProdotto']),
                                                 ('default_code', '=', line['DsCodProdotto'])])
                                        else:
                                            milor_account_code_id = self.env['product.account.code'].search([('name','=',line['IdProdotto'])])
                                            if milor_account_code_id:
                                                product_id = self.env['product.product'].search([('milor_account_code_id','=',milor_account_code_id.id),('default_code','=',line['DsCodProdotto'])])
                                    else:
                                        product_id = self.env['product.product'].search([('name','=',line['Descrizione'])])
                                    invoice_line_form.product_id = product_id
                                    invoice_line_form.account_id = account_os1.account_id
                                    invoice_line_form.price_unit = line['Prezzo']
                                    invoice_line_form.name = product_id.display_name if product_id and product_id.display_name else line['Descrizione']
                                    invoice_line_form.quantity = line['Quantita']
            new_invoice = invoice_form.save()
            try:
                if bool(errore_in_line):
                    raise Exception
                if not bool(account_os1.jump_doc_os1_line):
                    for line in new_invoice.invoice_line_ids:
                        line.document_os1_line_id = int(line.name)
                        line.name = line.product_id.display_name
                        if bool(line.document_os1_line_id.sale_order_line_id):
                            line.sale_line_ids = [[4, line.document_os1_line_id.sale_order_line_id.id]]

                new_invoice.action_post()
                new_invoice.write({'name':invoice['NumDocumento'],
                                   'invoice_origin': '{} | {}'.format(",".join(str(i) for i in list_invoice_origin), ",".join(str(i) for i in sale_order_names))})
                vals = {'name':invoice['KTestaDoc'],
                        'document_number':invoice['NumDocumento'],
                        'document_os1_id':self.id,
                        'invoice_id':new_invoice.id}
                self.env['syd_os1.doc_os1.invoice_done'].create(vals)
                self.write({'flagInvoiceNotImported':False,
                            'flagInvoiced':True})
            except Exception as error:
                vals = {'type':'invoice',
                        'message_error':'Per DOC OS1: {} con key: {} si ha questo Errore: {}'.format(self.display_name, self.key_returned, error),
                        'model':self._name,
                        'res_id':self.id,
                        'os1_account_id':self.account_os1_id.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
                new_invoice.unlink()
                self.env['ir.logging'].create({'name':'Create DOC OS1',
                                               'func':'Create DOC OS1',
                                               'line':1,
                                               'message':'Per DOC OS1: {} con key: {} si ha questo Errore: {}'.format(self.display_name, self.key_returned, error),
                                               'path':'Create DOC OS1',
                                               'type':'server'})

    def isFullyInvoiced(self):
        for line in self.doc_os1_line_ids:
            if not line.is_invoiced:
                return line.is_invoiced
        return True

    def createInvoice(self, response, os1_account):
        if type(response) == list:
            if self.testResponseOS1Invoice(response, os1_account):
                for invoice in response:
                    if self.invoiceIsDone(invoice['KTestaDoc'], invoice['NumDocumento']):
                        continue
                    else:
                        self._createInvoice(invoice)
            if self.flagInvoiceNotImported or self.flagInvoiced:
                return 'invoiced'
            else:
                return self.state
        else:
            self.env['ir.logging'].create({'name':'Create DOC OS1',
                                           'func':'Create DOC OS1',
                                           'line':1,
                                           'message':'Per DOC OS1: {} con key: {} si ha questo Errore: {}'.format(self.display_name, self.key_returned, error),
                                           'path':'Create DOC OS1',
                                           'type':'server'})
            return False

    def setInvoiced(self, response, os1_account):
        ris = self.createInvoice(response, os1_account)
        if bool(ris):
            self.write({'state':ris})

    def create_invoice_from_one_doc_os1(self):
        self.env['syd_os1.os1.account']._getInvoiceCode(self.account_os1_id, self)

    #STATE INVOICE

    def setInvoicedState(self, response, os1_account):
        if type(response) == list:
            if len(response):
                if self.testResponseOS1Invoice(response, os1_account):
                    self.write({'state':'invoiced'})
        else:
            raise Exception

    #STATE DDT

    def setDDTState(self, response, os1_account):
        if type(response) == list:
            if len(response):
                self.write({'state':'ddt',
                            'flagDdt':True})
        else:
            raise Exception

    #PAID
    def _createPayment(self, payment):
        invoice_done_id = self.invoice_done_ids.filtered(lambda invoice_done_id: invoice_done_id.document_number == payment['NumDocumento'])
        invoice_done_id.write({'is_paid':invoice_done_id.invoice_id.createPayment()})

    def invoiceIsPaid(self, document_number):
        invoice_done_id = self.invoice_done_ids.filtered(lambda invoice_done_id: invoice_done_id.document_number == document_number)
        if bool(invoice_done_id):
            if invoice_done_id.invoice_id.state != 'posted':
                return invoice_done_id.is_paid
        return False

    def isFullypayment(self):
        for invoice_done_id in self.invoice_done_ids:
            if not invoice_done_id.is_paid:
                return invoice_done_id.is_paid
        return True

    def createPayment(self, response, os1_account):
        if self.testResponseOS1Invoice(response, os1_account):
            for payment in response:
                if self.invoiceIsPaid(payment['NumDocumento']):
                    continue
                else:
                    self._createPayment(payment)

        if self.isFullypayment():
            return 'paid'
        else:
            return self.state

    def setPaid(self, response, os1_account):
        self.write({'state':self.createPayment(response, os1_account)})