# -*- coding: utf-8 -*-

import logging
import json
import requests
import base64
import dateutil.parser
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
import pytz
import time
from odoo.tests.common import Form

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#Timeout 10 min
TIMEOUT = 600

KNOW_ERROR_CODES = {
    401: _('Unauthorized ! The necessary authentication credentials are not present in the request or are incorrect..'),
    400: _('Bad Request! The request was not understood by the server, generally due to bad syntax.'),
    404: _('Not Found ! The requested resource could not be found (incorrect or invalid URI).'),
    500: _('Internal Server Error ! An internal error occurred in . Please contact our API support team : api@support..com so that our support team could investigate it.'),
    429: _('Too Many Requests! The request was not accepted because the application has exceeded the rate limit. See the API Rate Limit documentation for a breakdown of \'s rate-limiting mechanism.'),
    501: _('Not Implemented! The requested endpoint is not available on that particular resource, e.g: currently we do not support POST for the users resource.'),
    504: _('Gateway Timeout! The request could not complete in time. Try breaking it down with our support team.')
}

class OS1ErrorSystemOS1(models.Model):
    _name = 'syd_os1.os1.error_os1'
    _description = 'OS1 Error system'
    
    type = fields.Selection([('contact','Contatto'),
                             ('invoice','Fattura DOC OS1'),
                             ('other','Altro')], string="Type")
    message_error = fields.Char('Error')
    model = fields.Char('Model')
    res_id = fields.Integer('Resource ID')
    
    os1_account_id = fields.Many2one('syd_os1.os1.account', string="OS1 account")

class OS1Account(models.Model):
    _name = 'syd_os1.os1.account'
    _description = 'OS1 Account'
    _inherit = ['mail.thread']
    
    name = fields.Char(string='Account Name', required=True)
    active = fields.Boolean('Active', track_visibility='onchange')
    color = fields.Integer(string='Color Index')
    
    #OS1 configuraton
    api_url = fields.Char("Service URL", track_visibility='onchange')
    api_version = fields.Char("API version", track_visibility='onchange')
    port = fields.Char('Porta API', track_visibility='onchange')
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    id_ditta = fields.Char('IdDitta', track_visibility='onchange')
    categ_id = fields.Many2one('product.category', 'Categoria spese trasporto', track_visibility='onchange')
    categ_product_packaging_id = fields.Many2one('product.category', 'Categoria prodotti packaging', track_visibility='onchange')
    categ_product_discount_id = fields.Many2one('product.category', 'Categoria prodotti Discount', track_visibility='onchange')
    journal_id = fields.Many2one('account.journal', 'Journal')
    journal_ddt_id = fields.Many2one('account.journal', 'Journal DDT')
    jump_doc_os1_line = fields.Boolean('Ignorare le righe')
    account_id = fields.Many2one('account.account', string='Account')
    product_id = fields.Many2one('product.product', string="Prodotto non riconosciuto")
    product_delivery_id = fields.Many2one('product.product', string="Prodotto Trasporto OS1")
    product_descriptive_id = fields.Many2one('product.product', string="Prodotto descrittivo OS1")
    
    #OS1 daily fees
    date_daily_fees = fields.Date('Date daily fees')
    date_daily_fees_from_date = fields.Date('Date daily fees from date')
    journal_inv_daily_fees_id = fields.Many2one('account.journal', 'Journal Vendite daily fees')
    journal_nc_daily_fees_id = fields.Many2one('account.journal', 'Journal Note di credito daily fees')
    
    #OS1 access Info    
    username = fields.Char("Username")
    password = fields.Char("Password")
    token = fields.Char("Token")
    token_expired = fields.Datetime("scadenza Token")
    
    #last operation details
    last_request = fields.Datetime('Lase request to OS1')
    from_date_invoice = fields.Datetime('From date request invoice')
    to_date_invoice = fields.Datetime('To date request invoice')
    
    #Error system OS1
    error_system_os1_ids = fields.One2many('syd_os1.os1.error_os1', 'os1_account_id', string="List of error system OS1")
    document_os1_ids = fields.One2many('syd_os1.doc_os1', 'account_os1_id', string="List of document OS1")
    
    @api.constrains('api_url','api_version','port','id_ditta')
    def checkConnection(self):
        self.action_test_connection()
    
    @api.model
    def getAccountOS1(self):
        account_os1 = self.env['syd_os1.os1.account'].search([('company_id','=',self.env.company.id)])
        if not bool(account_os1):
            raise UserError("Bisogna impostare un account OS1 per la tua azienda")
        return account_os1
    
    @api.model
    def create(self, vals):
        os1_account_id = super(OS1Account, self).create(vals)
        if bool(self.env['syd_os1.os1.account'].search([('company_id','=',self.env.company.id),('id','!=',os1_account_id.id)])):
            raise UserError("Non puoi creare più di un account OS1 per la stessa azienda {}".format(self.env.company.display_name))
        if bool(os1_account_id.to_date_invoice) and  os1_account_id.from_date_invoice > os1_account_id.to_date_invoice:
            os1_account_id.to_date_invoice = os1_account_id.from_date_invoice + relativedelta(days=1)
        return os1_account_id
    
    def write(self, vals):
        res = super(OS1Account, self).write(vals)
        if bool(self.to_date_invoice) and self.from_date_invoice > self.to_date_invoice:
            raise UserError("devi inserirre una data TO maggiore della data FROM")
        return res
    
    def showDocumentOS1(self):
        [action] = self.env.ref('syd_os1.action_document_os1').read()
        action['domain'] = "[('id','in',{})]".format(self.document_os1_ids.ids)
        return action
    
    def createProductOS1(self, data):
        headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        response = self._synch_with_endopint(http_method = "POST",
                                                    service_endpoint = "rest/idea/milor/importarticoli",
                                                    params = {},
                                                    json = data,
                                                    headers = headers)
        if len(response) > 0:
            if response['Vresult']:
                if bool(response['VKSegnalazioni']):
                    return False, response['VKSegnalazioni']
                return response['Vresult'], False
            else:
                return False, response['VKSegnalazioni']
        else:
            return False, "Nessuna risposta dal Sistema OS1 Response: {} | Metodo Crea Product in OS1 data: {}".format(response, data)
        
    def createDocumentOS1Line(self, data):
        headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        response = self._synch_with_endopint(http_method = "POST",
                                                    service_endpoint = "rest/idea/milor/importdistinte",
                                                    params = {},
                                                    json = data,
                                                    headers = headers)
        if len(response) > 0:
            if response['Vresult']:
                if 'VKKey' not in response or bool(response['VKSegnalazioni']):
                    return False, response['VKSegnalazioni']
                else:
                    return response['VKKey'], False
            else:
                return False, response['VKSegnalazioni']
        else:
            return False, "Nessuna risposta dal Sistema OS1 Response: {} | Metodo createDocumentOS1Line data: {}".format(response, data)
    
    def createError(self, object, mex):
        vals = {'type':'contact',
                'message_error':mex,
                'model':object._name,
                'res_id':object.id,
                'os1_account_id':self.id}
        self.env['syd_os1.os1.error_os1'].create(vals)
    
    def createCustomers(self, partner, cron = False):
        if not partner.already_sent:
            headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                       'Content-Type':'application/json'}
            
            data = {'RagioneSociale':partner.display_name}
            
            if bool(partner.street):
                data['Indirizzo'] = partner.street
            if bool(partner.city):
                data['Localita'] = partner.city.upper()
            if bool(partner.zip):
                data['IdCap'] = partner.zip
            if bool(partner.state_id.name):
                data['IdProvincia'] = partner.state_id.code
            if bool(partner.phone):
                data['Telefono1'] = partner.phone
            if bool(partner.phone2):
                data['Telefono2'] = partner.phone2
            if bool(partner.mobile):
                data['TelCellulare'] = partner.mobile
            if bool(partner.email):
                data['EMail'] = partner.email
            if bool(partner.website):
                data['IndirizzoWEB'] = partner.website
            vat = partner.vat
            if bool(vat):
                data['PartitaIVA'] = partner.vat[2:].replace(' ', '')
            if bool(partner.l10n_it_codice_fiscale):
                data['CodiceFiscale'] = partner.l10n_it_codice_fiscale
            if bool(partner.country_id):
                if bool(partner.country_id.os1_id_nation):
                    data['IdNazione'] = partner.country_id.os1_id_nation.zfill(3)
            if bool(partner.salesman_partner_id):
                if bool(partner.salesman_partner_id.fm_id):
                    data['IdAgente1'] = partner.salesman_partner_id.fm_id.zfill(3)
            if bool(partner.parent_id):
                if bool(partner.parent_id.property_product_pricelist):
                    if bool(partner.parent_id.property_product_pricelist.currency_id):
                        data['IdDivisa'] = partner.parent_id.property_product_pricelist.currency_id.os1_code.zfill(3)
                    else:
                        data['IdDivisa'] = ''
            else:
                if bool(partner.property_product_pricelist):
                    if bool(partner.property_product_pricelist.currency_id):
                        data['IdDivisa'] = partner.property_product_pricelist.currency_id.os1_code.zfill(3)
                    else:
                        data['IdDivisa'] = ''
            note = []
            if bool(partner.l10n_it_pa_index):
                note.append(partner.l10n_it_pa_index)
            if bool(partner.l10n_it_pec_email):
                note.append(partner.l10n_it_pec_email)
            for bank in partner.bank_ids:
                if bool(bank.acc_number):
                    note.append(bank.acc_number)
            if len(note) != 0:
                data['Note01'] = ",".join(str(i) for i in note)
            if bool(partner.property_payment_term_id):
                data['IdPagamento'] = partner.property_payment_term_id.os1_code
            
            response = self._synch_with_endopint(http_method = "POST",
                                                        service_endpoint = "rest/idea/milor/importclienti",
                                                        params = {},
                                                        json = data,
                                                        headers = headers)
            if len(response) != 0:
                if response['Vresult']:
                    if response['VRecordCount'] != 1:
                        if bool(cron):
                            self.createError(partner, "Problemi di invio dati ad OS1, il contatto con id: {} non è stato creato su OS1, questi sono i dati inseriti: {}, l'errore è: {}".format(partner.id, data, response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                        else:
                            raise UserError("[Creazione contatto su OS1] Problemi di invio dati ad OS1: {}".format(response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                else:
                    if bool(cron):
                        self.createError(partner, "Problemi di invio dati ad OS1, il contatto con id: {} non è stato creato su OS1, questi sono i dati inseriti: {}, l'errore è: {}".format(partner.id, data, response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                    else:
                        raise UserError("[Creazione contatto su OS1]Problemi di invio dati ad OS1: {}".format(response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))        
            else:
                self.createError(partner, "Sistema non raggiungibile")
                self._cr.commit()
                raise UserError("Sistema non raggiungibile")
            partner.write({'already_sent':True,
                           'get_unique_code':True,
                           'fm_id':response['VKKey']})
    
    def createTemporaryCustomers(self, partner, cron = False):
        if not partner.already_sent:
            headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                       'Content-Type':'application/json'}
            
            data = {'IdConto':str(partner.id), #lui accetta qualsiasi valore, inserito l'ID del contatto per poi poter cercare il contatto finale tramite l'id
                    'RagioneSociale':partner.display_name
                    }
            
            if bool(partner.street):
                data['Indirizzo'] = partner.street
            if bool(partner.city):
                data['Localita'] = partner.city.upper()
            if bool(partner.zip):
                data['IdCap'] = partner.zip
            if bool(partner.state_id.name):
                data['IdProvincia'] = partner.state_id.code
            if bool(partner.phone):
                data['Telefono1'] = partner.phone
            if bool(partner.property_payment_term_id):
                data['IdPagamento'] = partner.property_payment_term_id.os1_code
            if bool(partner.phone2):
                data['Telefono2'] = partner.phone2
            if bool(partner.mobile):
                data['TelCellulare'] = partner.mobile
            if bool(partner.email):
                data['EMail'] = partner.email
            if bool(partner.website):
                data['IndirizzoWEB'] = partner.website
            vat = partner.vat
            if bool(vat):
                data['PartitaIVA'] = partner.vat[2:].replace(' ', '')
            if bool(partner.l10n_it_codice_fiscale):
                data['CodiceFiscale'] = partner.l10n_it_codice_fiscale
            if bool(partner.country_id):
                if bool(partner.country_id.os1_id_nation):
                    data['IdNazione'] = partner.country_id.os1_id_nation.zfill(3)
            if bool(partner.salesman_partner_id):
                if bool(partner.salesman_partner_id.fm_id):
                    data['IdAgente1'] = partner.salesman_partner_id.fm_id.zfill(3)
            if bool(partner.parent_id):
                if bool(partner.parent_id.property_product_pricelist):
                    if bool(partner.parent_id.property_product_pricelist.currency_id):
                        data['IdDivisa'] = partner.parent_id.property_product_pricelist.currency_id.os1_code.zfill(3)
                    else:
                        data['IdDivisa'] = ''
            else:
                if bool(partner.property_product_pricelist):
                    if bool(partner.property_product_pricelist.currency_id):
                        data['IdDivisa'] = partner.property_product_pricelist.currency_id.os1_code.zfill(3)
                    else:
                        data['IdDivisa'] = ''
            
            note = []
            if bool(partner.l10n_it_pa_index):
                note.append(partner.l10n_it_pa_index)
            if bool(partner.l10n_it_pec_email):
                note.append(partner.l10n_it_pec_email)
            for bank in partner.bank_ids:
                if bool(bank.acc_number):
                    note.append(bank.acc_number)
            
            if len(note) != 0:
                data['Note01'] = ",".join(str(i) for i in note)
            
            response = self._synch_with_endopint(http_method = "POST",
                                                        service_endpoint = "rest/idea/milor/importclientiprovv",
                                                        params = {},
                                                        json = data,
                                                        headers = headers)
            if len(response) != 0:
                if response['Vresult']:
                    if response['VRecordCount'] != 1:
                        if bool(cron):
                            self.createError(partner, "Problemi di invio dati ad OS1, il contatto con id: {} non è stato creato su OS1, questi sono i dati inseriti: {}, l'errore è: {}".format(partner.id, data, response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                        else:
                            raise UserError("[Creazione contatto su OS1] Problemi di invio dati ad OS1: {}".format(response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                else:
                    if bool(cron):
                        self.createError(partner, "Problemi di invio dati ad OS1, il contatto con id: {} non è stato creato su OS1, questi sono i dati inseriti: {}, l'errore è: {}".format(partner.id, data, response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))
                    else:
                        raise UserError("[Creazione contatto su OS1]Problemi di invio dati ad OS1: {}".format(response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ''))        
            else:
                self.createError(partner, "Sistema non raggiungibile")
                self._cr.commit()
                raise UserError("Sistema non raggiungibile")
            partner.already_sent = True
#     CRON
    
    @api.model
    def _getDDTState(self, os1_account, doc_os1):
        headers = {'Authorization':'Bearer {}'.format(os1_account.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        sub_data = {'IdKeyFM':"{}".format(doc_os1.key_returned)}#key_returned è il campo che è stato assegnato al DOC OS1 dopo la creazione della distinta su OS1
        
        response = os1_account._synch_with_endopint(http_method = "GET",
                                                service_endpoint = "rest/idea/milor/listaddt",
                                                params = {},
                                                json = sub_data,
                                                headers = headers)
        
        if 'status_code' not in response:
            try:
                doc_os1.setDDTState(response, os1_account)
            except Exception as error:
                vals = {'type':'invoice',
                        'message_error':"IdKeyFM: {}, Stato DDT non riuscito a settare: {}".format(doc_os1.key_returned, response),
                        'model':doc_os1._name,
                        'res_id':doc_os1.id,
                        'os1_account_id':os1_account.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
        else:
            vals = {'type':'invoice',
                    'message_error':'Fallita Request per lo stato del DDT del DOC OS1: {} Status Code: {}, Segnalazione: {}.'.format(doc_os1.id, response['status_code'], response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ""),
                    'model':doc_os1._name,
                    'res_id':doc_os1.id,
                    'os1_account_id':os1_account.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
    
    @api.model
    def getDDTState(self):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            for doc_os1 in self.env['syd_os1.doc_os1'].search([('account_os1_id','=',os1_account.id),('state','=','done')]):
                self._getDDTState(os1_account, doc_os1)
    
    @api.model
    def _getInvoiceState(self, os1_account, doc_os1):
        headers = {'Authorization':'Bearer {}'.format(os1_account.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        sub_data = {'IdKeyFM':"{}".format(doc_os1.key_returned)}#key_returned è il campo che è stato assegnato al DOC OS1 dopo la creazione della distinta su OS1
        
        response = os1_account._synch_with_endopint(http_method = "GET",
                                                service_endpoint = "rest/idea/milor/listafatture",
                                                params = {},
                                                json = sub_data,
                                                headers = headers)
        
        if 'status_code' not in response:
            try:
                doc_os1.setInvoicedState(response, os1_account)
            except Exception as error:
                vals = {'type':'invoice',
                        'message_error':"IdKeyFM: {}, Stato Invoice non riuscito a settare: {}".format(doc_os1.key_returned, response),
                        'model':doc_os1._name,
                        'res_id':doc_os1.id,
                        'os1_account_id':os1_account.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
        else:
            vals = {'type':'invoice',
                    'message_error':'Fallita Request per lo stato della fattura del DOC OS1: {} Status Code: {}, Segnalazione: {}.'.format(doc_os1.id, response['status_code'], response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ""),
                    'model':doc_os1._name,
                    'res_id':doc_os1.id,
                    'os1_account_id':os1_account.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
    
    @api.model
    def getInvoiceState(self):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            for doc_os1 in self.env['syd_os1.doc_os1'].search([('account_os1_id','=',os1_account.id),'|',('state','in',['done','ddt']),('flagInvoiceNotImported','=',True),('flagInvoiced','=',False)]):
                self._getInvoiceState(os1_account, doc_os1)
    
    @api.model
    def _getInvoiceCode(self, os1_account, doc_os1):
        headers = {'Authorization':'Bearer {}'.format(os1_account.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        sub_data = {'IdKeyFM':"{}".format(doc_os1.key_returned)}#key_returned è il campo che è stato assegnato al DOC OS1 dopo la creazione della distinta su OS1
        
        response = os1_account._synch_with_endopint(http_method = "GET",
                                                service_endpoint = "rest/idea/milor/listafatture",
                                                params = {},
                                                json = sub_data,
                                                headers = headers)
        
        if 'status_code' not in response:
            try:
                doc_os1.setInvoiced(response, os1_account)
            except Exception as error:
                doc_os1.write({'flagInvoiceNotImported':True,
                               'flagInvoiced':False,
                               'state':'invoiced'})
                vals = {'type':'invoice',
                        'message_error':"IdKeyFM: {}, Fattura non importata: {}, ERRORE:{}".format(doc_os1.key_returned, response, error),
                        'model':doc_os1._name,
                        'res_id':doc_os1.id,
                        'os1_account_id':os1_account.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
        else:
            vals = {'type':'invoice',
                    'message_error':'Fallita Request per la fatturazione del DOC OS1: {} Status Code: {}, Segnalazione: {}.'.format(doc_os1.id, response['status_code'], response['VKSegnalazioni'] if 'VKSegnalazioni' in response else ""),
                    'model':doc_os1._name,
                    'res_id':doc_os1.id,
                    'os1_account_id':os1_account.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
    
    @api.model
    def getInvoiceCode(self):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            for doc_os1 in self.env['syd_os1.doc_os1'].search([('account_os1_id','=',os1_account.id),'|',('state','in',['done','ddt','invoiced']),('flagInvoiceNotImported','=',True),('flagInvoiced','=',False)]):
                self._getInvoiceCode(os1_account, doc_os1)
                self._cr.commit()
                    
    @api.model
    def deleteErrors(self):
        six_months = date.today() + relativedelta(months=-6)
        line_error = self.env['syd_os1.os1.error_os1'].search([('create_date','<',six_months)])
        line_error.unlink()
    
    def create_daily_fees_from_this_date(self):
        date_today = datetime.datetime.now().date()
        while (date_today > self.date_daily_fees_from_date):
            self.env['syd_os1.os1.account'].create_daily_fees(True, self.date_daily_fees_from_date)
            self.date_daily_fees_from_date += relativedelta(days=1)
    
    @api.model
    def create_daily_fees(self, change_date=False, date_daily_fees_to_scan=False):
        date_today = datetime.datetime.now()
        for os1_account_id in self.env['syd_os1.os1.account'].search([('active','=',True)]):
            
            if not bool(date_daily_fees_to_scan):
                date_daily_fees = os1_account_id.date_daily_fees
            else:
                date_daily_fees = date_daily_fees_to_scan

            headers = {'Authorization':'Bearer {}'.format(os1_account_id.action_update_access_token()),
                       'Content-Type':'application/json'}
            
            dict_iva = {}
            move_ids = self.env['account.move'].search([('journal_id','=',os1_account_id.journal_inv_daily_fees_id.id),('invoice_date_due','=',date_daily_fees),('type','=','out_invoice'),('state','=','posted')])
            move_in_line_ids = self.env['account.move.line'].search([('move_id','in',move_ids.ids),('exclude_from_invoice_tab','=',False)])
            
            move_ids = self.env['account.move'].search([('journal_id','=',os1_account_id.journal_nc_daily_fees_id.id),('invoice_date_due','=',date_daily_fees),('type','=','out_refund'),('state','=','posted')])
            move_nc_line_ids = self.env['account.move.line'].search([('move_id','in',move_ids.ids),('exclude_from_invoice_tab','=',False)])
            
            for move_in_line_id in move_in_line_ids:
                for tax_id in move_in_line_id.tax_ids:
                    if tax_id.os1_code not in dict_iva:
                        dict_iva[tax_id.os1_code] = 0
                    dict_iva[tax_id.os1_code] += move_in_line_id.price_subtotal
            
            for move_nc_line_id in move_nc_line_ids:
                for tax_id in move_nc_line_id.tax_ids:
                    if tax_id.os1_code not in dict_iva:
                        dict_iva[tax_id.os1_code] = 0
                    dict_iva[tax_id.os1_code] -= abs(move_nc_line_id.price_subtotal)
            
            data = []
            for element_iva in dict_iva:
                data.append({'DataMovimento':date_daily_fees,
                             'IdIva':element_iva,
                             'NumRegistro':'1',
                             'Importo':dict_iva[element_iva]})
            
            response = os1_account_id._synch_with_endopint(http_method = "POST",
                                                       service_endpoint = "rest/idea/milor/importcorrispettivi",
                                                       params = {},
                                                       json = data,
                                                       headers = headers)
            if len(response) > 0:
                if response['Vresult']:
                    move_ids.write({'already_sent':True})
                    if bool(change_date):
                        os1_account_id.date_daily_fees = date_today
    @api.model
    def getPaymentCode(self):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            for doc_os1 in self.env['syd_os1.doc_os1'].search([('state','=','invoiced'),('flagInvoiced','=',True),('account_os1_id','=',os1_account.id)]):
                headers = {'Authorization':'Bearer {}'.format(os1_account.action_update_access_token()),
                           'Content-Type':'application/json'}
                for invoice_done_id in doc_os1.invoice_done_ids.filtered(lambda invoice_done_id: invoice_done_id.is_paid == False):
                    sub_data = {'IdQuery':'ListascadenzeClienti',
                                'IdCondizioneWhere': "IdConto = '{}' and NumDocumento = '{}'".format(doc_os1.partner_id.fm_id.zfill(8), invoice_done_id.document_number)
                                }#Il campo NumDocumento non è il Campo corretto per ricercare la fattura di una certa distinta
                    
                    
                    response = os1_account._synch_with_endopint(http_method = "GET",
                                                            service_endpoint = "rest/idea/milor/ListaDati",
                                                            params = {},
                                                            json = sub_data,
                                                            headers = headers)
                    
                    lenght = len(response)
                    if lenght == 1:
                        doc_os1.setPaid(response, os1_account)
                    else:
                        if lenght > 1:
                            vals = {'type':'contact',
                                    'message_error':"the contacts that have been found in the OS1 system are {} for the contact with ID: {}".format(lenght, partner.id),
                                    'model':doc_os1._name,
                                    'res_id':doc_os1.id,
                                    'os1_account_id':self.id}
                            self.env['syd_os1.os1.error_os1'].create(vals)
    
    #Non toccare i campi:
    #    se non trova il codice filemaker code
    #        Nome
    #        Email
    #    sheep to
    #        street
    #        zip
    #        city
    
    def get_value_unique_code(self, partner, response):
    #Agenti
        agente1_id = self.env['res.partner'].search([('fm_id','=',response['IdAgente1'])])
        agente2_id = self.env['res.partner'].search([('fm_id','=',response['IdAgente2'])])
    #provincia
        provincia_id = self.env['res.country.state'].search([('os1_code','=',response['IdProvincia'])])#Aggiungere gli ID
    #Nazione
        nation_id = self.env['res.country'].search([('os1_id_nation','=',response['IdNazione'])])
    #Corriere
        spedizioniere1_id = self.env['res.partner'].search([('fm_id','=',response['IdSpedizione1'])])
        spedizioniere2_id = self.env['res.partner'].search([('fm_id','=',response['IdSpedizione2'])])
    #Termini di pagamento
        property_payment_term_id = self.env['account.payment.term'].search([('os1_code','=',response['IdPagamento'])])
    #TAG
        tag_id = self.env['res.partner.category'].search([('os1_code','=',response['IdAttivita'])])#Aggiungere gli ID
    #Delivery Method
        property_delivery_carrier_id = self.env['delivery.carrier'].search([('os1_code','=',response['IdTipoTrasporto'])])
    #active
        active = True if bool(response['DataObsoleto']) else False
    #Divisa
        currency_id = self.env['res.currency'].search([('os_code','=',response['IdDivisa'])])
        
        return {'fm_type':response['IdContoTp'],
                'fm_id':response['IdConto'],
                'get_unique_code':True,
                'already_sent':False,
                'name':'{}{}'.format(response['RagioneSociale'], ' {}'.format(response['DatiAggiuntivi']) if bool(response['DatiAggiuntivi']) else '').upper(),
                'street':response['Indirizzo'].upper() if bool(response['Indirizzo']) else '',
                'street2':response['Indirizzo2'].upper() if bool(response['Indirizzo2']) else '',
                'zip':response['IdCap'],
                'city':response['Localita'].upper() if bool(response['Localita']) else '',
                'state_id':provincia_id.id,
                'country_id':nation_id.id if bool(nation_id) else False,
                'vat':response['PartitaIVA'],
                'l10n_it_codice_fiscale':response['CodiceFiscale'],
                'phone':response['Telefono1'],
                'phone2':response['Telefono2'],
                'mobile':response['TelCellulare'],
                'fax':response['TelFax'],
                'email':response['Email'],
                'website':response['IndirizzoWEB'],
                'property_payment_term_id':property_payment_term_id.id,
                'categoty_id':[[4, tag_id.id]] if bool(tag_id) else [[6, 0, partner.categoty_id.ids]],
                'salesman_partner_id':agente1_id.id if bool(agente1_id) and len(agente1_id) == 1 else False,
                'salesman_partner_2_id':agente2_id.id if bool(agente2_id) and len(agente2_id) == 1 else False,
                'currency_id':currency_id.id,
                'carrier_partner_id':spedizioniere1_id.id if bool(spedizioniere1_id) and len(spedizioniere1_id) == 1 else False,
                'carrier_partner_2_id':spedizioniere2_id.id if bool(spedizioniere2_id) and len(spedizioniere2_id) == 1 else False,
                'property_delivery_carrier_id':property_delivery_carrier_id.id,
                'active':active,
                'l10n_it_pec_email':response['EMailPEC']}
    
    @api.model
    def getUniqueCode(self, partner_ids = False):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            if bool(partner_ids):
                partners = partner_ids.filtered(lambda rp: rp.get_unique_code == False and rp.already_sent == True) 
            else: 
                partners = self.env['res.partner'].search([('get_unique_code','=',False),('already_sent','=',True)])
            for partner in partners:
                headers = {'Authorization':'Bearer {}'.format(os1_account.action_update_access_token()),
                           'Content-Type':'application/json'}
                
                sub_data = {'IdQuery':'Clienti',
                            'IdCondizioneWhere': "IdConto = '{}'".format(partner.id)
                            }
                
                
                response = os1_account._synch_with_endopint(http_method = "GET",
                                                        service_endpoint = "rest/idea/milor/ListaDati",
                                                        params = {},
                                                        json = sub_data,
                                                        headers = headers)
                
                lenght = len(response)
                if lenght == 1:
                    partner.write(self.get_value_unique_code(partner, response[lenght - 1]))
                else:
                    if lenght > 1:
                        vals = {'type':'contact',
                                'message_error':"the contacts that have been found in the OS1 system are {} for the contact with ID: {}".format(lenght, partner.id),
                                'model':partner._name,
                                'res_id':partner.id,
                                'os1_account_id':self.id}
                        self.env['syd_os1.os1.error_os1'].create(vals)
    
    def action_test_connection(self):
        if self._action_test_connection():
            self.action_update_access_token()
            self.write({'active':True})
        else:
            self.write({'active':False,
                    'token':False,
                    'token_expired':False})
    
    def os1_action_archive_unarchive(self):
        if self.active:
            self.write({'active':False,
                        'token':False,
                        'token_expired':False})
        else:
            self.action_test_connection()
        return True
    
    # CONNESSIONE OS1
    
    def _action_test_connection(self):
        self.ensure_one()
        result = self._get_access_token()
        if 'IsVerified' in result:
            return bool(result['IsVerified'])
        else:
            return False

    def action_update_access_token(self):
        self.ensure_one()
        if not bool(self.token_expired) or datetime.datetime.utcnow() > self.token_expired:
            result = self._get_access_token()
            self.write({
                'token': result['Token'],
                'token_expired': dateutil.parser.parse(result['Expiration']).astimezone(pytz.utc).replace(tzinfo=None)
            })
            return result['Token']
        else:
            return self.token
    
    def _get_access_token(self):
        """
            Retrieves company level API Token, Company ID and API Base URI. Requires Admin credentials.
        """
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        return self._synch_with_endopint(
            http_method='POST', service_endpoint='rest/idea/token',
            params={}, data={'username':self.username,'password':self.password,'dbname':self.id_ditta}, headers=headers)

    def _synch_with_endopint(self, http_method, service_endpoint, params={}, data={}, headers={}, json={}):
        if params is None:
            params = {}

        if data is None:
            data = {}
        
        service_url = '{}:{}/{}{}'.format(self.api_url,self.port, self.api_version if bool(self.api_version) else '', service_endpoint)
        func = '{}:{}'.format(http_method, service_endpoint)
        response = {}

        try:
            message = 'BEFORE REQUEST: http_method: {}; service_url: {}; headers: {}; json:{}; params: {}; data:{}; timeout:{}'.format(http_method, service_url, headers, json, params, data, TIMEOUT)
            vals = {'type':'other',
                    'message_error':message,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            resp = requests.request(
                http_method, service_url,
                headers=headers,
                json=json,
                params=params,
                data=data, timeout=TIMEOUT)
            message = 'AFTER REQUEST: http_method: {}; service_url: {}; headers: {}; json:{}; params: {}; data:{}; timeout:{}'.format(http_method, service_url, headers, json, params, data, TIMEOUT)
            vals = {'type':'other',
                    'message_error':message,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            if resp.status_code != 200:
                response = {'status_code':resp.status_code,
                            'VKSegnalazioni':resp.text,
                            'Vresult':False}
            else:
                resp.raise_for_status()
                response = resp.json()

        except requests.HTTPError as ex:
            level = 'warning'
            if resp.status_code in KNOW_ERROR_CODES:
                message = KNOW_ERROR_CODES[resp.status_code]
            else:
                message = _('Unexpected error ! please report this to your administrator.')
                level = 'error'
            message = '{}'.format(resp.status_code)
            message = 'Message: {} || Level = {} || Path: {} || Func: {}'.format(message, level, http_method, func)
            vals = {'type':'other',
                    'message_error':message,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            self._cr.commit()
        except Exception as ex:
            message = '{}'.format(ex)
            level = 'error'
            message = 'Message: {} || Level = {} || Path: {} || Func: {}'.format(message, level, http_method, func)
            vals = {'type':'other',
                    'message_error':message,
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
            self._cr.commit()
        self.last_request = datetime.datetime.now()
        
        return response

    def _get_request_header(self, token):
        header = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Catch-Control": "no-cache",
            "X--ConsumerKey": 'key',
        }
        header["Authorization"] = 'Basic {}'.format(token)
        return header
    
    @api.model
    def get_nation_code(self):
        headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                   'Content-Type':'application/json'}
        
        sub_data = {'IdQuery':'Nazioni'}
        
        
        response = self._synch_with_endopint(http_method = "GET",
                                             service_endpoint = "rest/idea/milor/ListaDati",
                                             params = {},
                                             json = sub_data,
                                             headers = headers)
        
        if len(response) > 0:
            return response
        else:
            vals = {'type':'other',
                    'message_error':"Importazione Country Errata",
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
    
    def remaining_time_check(self, start_time, end_time, gap_max = 180):
        time_max = 1140 #19 minutes not to let the cron time out 
        if (end_time - start_time) > (time_max - gap_max):
            return True
        return False
    
    def _create_invoice(self, response, ddt=False):
        start_create_invoice = time.time()
        last_invoice_date = self.from_date_invoice
        for invoice in response:
            if self.remaining_time_check(start_create_invoice, time.time()):
                return True, last_invoice_date
            #For compatibility for Python versions, the idea was to use this line of code:
            #invoice_date = datetime.datetime.strptime(invoice['DataDocumento'], '%Y-%m-%dT%H:%M:%S.%f%z').date()
            invoice_date = invoice['DataDocumento'][:10]
            if invoice["IdCausale"] != 'PRO' and not bool(self.env['account.move'].search([('invoice_date','=',invoice_date),'|',('temp_name','=',invoice["NumDocumento"]),('name','=',invoice["NumDocumento"])])):
                try:
                    partner_id = self.env['res.partner'].search([('parent_id','=',False),
                                                                 ('fm_type','=','CL'),
                                                                 ('fm_id','=',invoice["IdCliente"].lstrip('0'))])
                    if len(partner_id) > 1:
                        vals = {'type':'invoice',
                                'message_error':"Per questa Fattura/DDT {} si ha IdCliente [{}] sono presenti questi Contatti: {}".format(invoice["NumDocumento"], invoice["IdCliente"], partner_id.ids),
                                'model':self._name,
                                'res_id':self.id,
                                'os1_account_id':self.id}
                        self.env['syd_os1.os1.error_os1'].create(vals)
                        
                        partner_id = partner_id[0]
                    dict_list_doc_os1_key = []
                    if invoice["SpeseTrasporto"] > 0:
                        invoice["Righe"].append({'IdKeyFM':'',
                                                 'IdProdotto':'',
                                                 'DsCodProdotto':'',
                                                 'Prezzo':invoice["SpeseTrasporto"],
                                                 'Quantita':1,
                                                 'Descrizione':'',
                                                 'Trasporto':True,
                                                 'TipoRigo':1})
                    if invoice['FlTipoDocumento'] == 1:
                        type_invoice = 'out_invoice'
                    elif invoice['FlTipoDocumento'] == 2:
                        type_invoice = 'out_refund'
                    elif invoice['FlTipoDocumento'] == 3:
                        type_invoice = 'in_refund'
                    else:
                        type_invoice = 'out_invoice'
                    
                    agente1_id = self.env['res.partner'].search([('fm_id','=',invoice['IdAgente1'])])
                    user_agente1_id = self.env['res.users']
                    if len(agente1_id) == 1:
                        user_agente1_id = self.env['res.users'].search([('partner_id','=',agente1_id.id)])
                    
                    with Form(self.env['account.move'].with_context(default_type=type_invoice)) as invoice_form:
                        invoice_form.partner_id = partner_id.commercial_partner_id
                        invoice_form.partner_shipping_id = partner_id
                        invoice_form.currency_id = self.env['res.currency'].search([('os1_code','=',str(int(invoice['IdDivisa'])))])
                        invoice_form.invoice_date = invoice_date
                        last_invoice_date = invoice_date
                        if not bool(ddt):
                            invoice_form.journal_id = self.journal_id
                        else:
                            invoice_form.journal_id = self.journal_ddt_id
                        #RIGHE FATTURA
                        for line in invoice['Righe']:
                            if self.remaining_time_check(start_create_invoice, time.time(), 120):
                                return True, last_invoice_date
                            if line['TipoRigo'] != 6:
                                if line['IdKeyFM'] != '' and line['IdKeyFM'] not in dict_list_doc_os1_key:
                                    dict_list_doc_os1_key.append(line['IdKeyFM'])
                                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                                    if line['TipoRigo'] == 3 or line['TipoRigo'] == 73:
                                        product_id = self.product_descriptive_id
                                    else:
                                        product_id = self.env['product.product']
                                        if bool(line['IdProdotto']) and bool(line['DsCodProdotto']):
                                            if self.company_id.account_code_os1 == 'milor_account_code':
                                                product_id = self.env['product.product'].search([
                                                    ('active', '=', True),
                                                    ('milor_account_code','=',line['IdProdotto']),
                                                    ('default_code', '=',line['DsCodProdotto'])
                                                ])
                                            else:
                                                milor_account_code_id = self.env['product.account.code'].search([('name','=',line['IdProdotto'])])
                                                product_id = self.env['product.product'].search([('active','=',True),('milor_account_code_id','=',milor_account_code_id.id),('default_code','=',line['DsCodProdotto'])])
                                        elif 'Trasporto' in line and bool(line['Trasporto']):
                                                product_id = self.product_delivery_id
                                        
                                        if not product_id:
                                            product_id = self.product_id
                                    if 'Sconto1' in line:
                                        discount = float(line['Sconto1'])
                                    else:
                                        discount = 0.0
                                        
                                    invoice_line_form.product_id = product_id
                                    invoice_line_form.account_id = self.account_id
                                    invoice_line_form.price_unit = line['Prezzo']
                                    invoice_line_form.name = product_id.display_name if bool(product_id.display_name) else line['Descrizione']
                                    invoice_line_form.quantity = line['Quantita']
                                    invoice_line_form.discount = discount
                    new_invoice = invoice_form.save()
                    new_invoice.write({'invoice_user_id':user_agente1_id.id,
                                       'invoice_imported_from_os1':True,
                                       'tot_document_euro':invoice['TotDocumentoEuro'],
                                       'tot_document_net_euro':invoice['TotImponibileEuro'],
                                       'tot_vat_euro':invoice['TotIvaEuro'],
                                       'transport_costs_euro':invoice['SpeseTrasportoEuro'],
                                       'miscellaneous_expenses_euro':invoice['SpeseVarieEuro'],
                                       'packaging_costs_euro':invoice['SpeseImballoEuro']})
                    if bool(partner_id) and not bool(ddt):
                        new_invoice.write({'name':invoice['NumDocumento']})
                        new_invoice.action_post()
                    else:
                        new_invoice.write({'temp_name':invoice['NumDocumento']})
                    doc_os1_ids = self.env['syd_os1.doc_os1'].search([('key_returned','in',dict_list_doc_os1_key)])
                    if bool(doc_os1_ids):
                        for doc_os1_id in doc_os1_ids:
                            vals = {'name':invoice['KTestaDoc'],
                                    'document_number':new_invoice.name,
                                    'document_os1_id':doc_os1_id.id,
                                    'invoice_id':new_invoice.id}
                            self.env['syd_os1.doc_os1.invoice_done'].create(vals)
                    self._cr.commit()
                except Exception as error:
                    if 'new_invoice' in locals():
                        if new_invoice.name == invoice['NumDocumento'] or new_invoice.temp_name == invoice['NumDocumento']:
                            new_invoice.unlink()
        return False, last_invoice_date
    
    def _create_invoice_from_os1(self):
        jump_write_date = True
        
        date_today = fields.Datetime.now()
        headers = {'Authorization':'Bearer {}'.format(self.action_update_access_token()),
                   'Content-Type':'application/json'}
        from_date_invoice = self.from_date_invoice.strftime("%Y-%m-%d") if bool(self.from_date_invoice) else date_today.strftime("%Y-%m-%d")
        to_date_invoice = self.to_date_invoice.strftime("%Y-%m-%d") if bool(self.to_date_invoice) else date_today.strftime("%Y-%m-%d")
        sub_data = {'DataDocumentoDa':"{}".format(from_date_invoice),
                    'DataDocumentoA':"{}".format(to_date_invoice)}
        
        #Fatture
        response = self._synch_with_endopint(http_method = "GET",
                                                    service_endpoint = "rest/idea/milor/listafatture",
                                                    params = {},
                                                    json = sub_data,
                                                    headers = headers)
        
        if 'status_code' not in response:
            try:
                jump_write_date, last_invoice_date = self._create_invoice(response)
            except Exception as error:
                vals = {'type':'invoice',
                        'message_error':"Errore importazione fattura dalla data: {} alla data: {} dell'account: {} |||| Errore: {}".format(from_date_invoice, to_date_invoice, self.name, error),
                        'model':self._name,
                        'res_id':self.id,
                        'os1_account_id':self.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
        else:
            vals = {'type':'invoice',
                    'message_error':'Fallita Request per la request delle fatture dalla data: {} alla data: {}'.format(from_date_invoice, to_date_invoice),
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
        
        #DDT
        response = self._synch_with_endopint(http_method = "GET",
                                                    service_endpoint = "rest/idea/milor/listaddt",
                                                    params = {},
                                                    json = sub_data,
                                                    headers = headers)
        
        if 'status_code' not in response:
            try:
                jump_write_date, last_invoice_date = self._create_invoice(response, True)
            except Exception as error:
                vals = {'type':'invoice',
                        'message_error':"Errore importazione DDT dalla data: {} alla data: {} dell'account: {} |||| Errore: {}".format(from_date_invoice, to_date_invoice, self.name, error),
                        'model':self._name,
                        'res_id':self.id,
                        'os1_account_id':self.id}
                self.env['syd_os1.os1.error_os1'].create(vals)
        else:
            vals = {'type':'invoice',
                    'message_error':'Fallita Request per la request delle DDT dalla data: {} alla data: {}'.format(from_date_invoice, to_date_invoice),
                    'model':self._name,
                    'res_id':self.id,
                    'os1_account_id':self.id}
            self.env['syd_os1.os1.error_os1'].create(vals)
        
        if not jump_write_date:
            new_from_date_invoice = self.to_date_invoice
            if not self.to_date_invoice:
                if to_date_invoice and not last_invoice_date < to_date_invoice:
                    new_from_date_invoice = to_date_invoice
                else:
                    new_from_date_invoice = last_invoice_date
            
            self.write({
                'from_date_invoice':new_from_date_invoice,
                'to_date_invoice':False
                })
        
        
    @api.model
    def create_invoice_from_os1(self):
        for os1_account in self.env['syd_os1.os1.account'].search([]):
            os1_account._create_invoice_from_os1()