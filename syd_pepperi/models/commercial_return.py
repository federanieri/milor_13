# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime

from odoo import api, fields, models, registry, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

PEPPERI_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"
PEPPERI_DATE_Z = "%Y-%m-%dZ"

# 'sent': 'Waiting for approval'
# 'sale': 'In planning'
# DO validated at least for one product: 'In Progress'
# When an order have all the product shipped: 'Closed'


    
class CommercialReturn(models.Model):
    _name = 'return.order.sheet'
    _inherit = ['return.order.sheet', 'pepperi.mixin']

    
    def _pepperi_status(self):
        return [('2', 'Submitted'), ('9', 'Waiting For Approval'), ('16', 'In Planning'), ('3', 'In Progress'), ('7', 'Closed')]

    pepperi_status = fields.Selection(
                                        _pepperi_status,
                                        string="Pepperi Status",
                                        copy=False,
                                        default=None,
                                        tracking=True
                                    )
    pepperi_flag = fields.Boolean(compute="_compute_pepperi_flag", store=True, default=False)
    pepperi_type = fields.Char('Pepperi Type',default="Credit Note")
    

    
    @api.depends('last_update_from_pepperi', 'write_date')
    def _compute_pepperi_flag(self):
        for rec in self.filtered(lambda s: s.from_pepperi and s.doc_cliente):
            if rec.write_date > rec.last_update_from_pepperi and rec.pepperi_status != '7':
                rec.pepperi_flag = True
            else:
                rec.pepperi_flag = False


    # def action_done(self):
    #     res = super(CommercialReturn, self).action_done()
    #     self.action_post_pepperi_status()
    #     return res
    #
    # def action_post_pepperi_status(self):
    #     datas = []
    #     for rec in self.filtered(lambda s: s.state in ['sent', 'sale'] and s.pepperi_status != '7' and s.from_pepperi and s.origin):
    #         data = rec.get_order_pepperi_status()
    #         try:
    #             pepperi_account = self.env['pepperi.account']._get_connection()
    #             data = self._post_pepperi_transaction(pepperi_account, params={}, data=data)
    #             if 'Status' in data:
    #                 ModificationDateTime = datetime.datetime.strptime(data.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
    #                 rec.write({
    #                         'pepperi_status': str(data.get('Status')),
    #                         'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    #                         'modification_datetime': data.get('ModificationDateTime'),
    #                     })
    #                 rec.message_post(body=_("TSATrackingNumber: %s" % data.get('TSATrackingNumber')))
    #             datas.append(data)
    #         except Exception as e:
    #             _logger.info(str(e))
    #             rec.message_post(body=_("%s \n %s" % (str(e), str(data))))
    #             _logger.info('Sale Order State synchronization response To pepperi ::: {}'.format(data))
    #             pepperi_account._log_message(str(e), _("Pepperi : Sale Order State synchronization response To pepperi issues: %s." % str(rec)), level="info", path="/transactions", func="_post_pepperi_status")
    #             self.env.cr.commit()
    #     return True

    # def get_order_pepperi_status(self):
    #     self.ensure_one()
    #     if self.state == 'sent' and self.pepperi_status != '9':
    #         return {
    #                 "InternalID": int(self.origin),
    #                 "Status": '9',
    #             }
    #
    #     if self.state == 'sale' and self.pepperi_status != '16':
    #         return {
    #                 "InternalID": int(self.origin),
    #                 "Status": '16',
    #             }
    #
    #     if sum(self.order_line.mapped('product_uom_qty')) == sum(self.order_line.mapped('qty_delivered')) and self.pepperi_status != '7':
    #         return {
    #                 "InternalID": int(self.origin),
    #                 "Status": '7',
    #                 "TSATrackingNumber":self._get_tracking_number()
    #             }
    #     elif sum(self.order_line.mapped('qty_delivered')) > 0 and self.pepperi_status != '3':
    #         return {
    #                 "InternalID": int(self.origin),
    #                 "Status": '3',
    #                 "TSATrackingNumber":self._get_tracking_number()
    #             }
    #     return {}

    def _prepare_order_line_data(self, pepperi_account, automatic, transactions_line,transaction=False):
        line_data = []
        for line in transactions_line:
            item = line['Item']
            item_data = item.get('Data')
            P_ExternalId = item_data.get('ExternalID')
            product_product = self.env['product.product']
            reason=False
            if transaction.get('TSAReasonforReturnHeader',''):
                reason = self.env['return.order.reason'].search([('name','=',transaction.get('TSAReasonforReturnHeader',''))],limit=1)
                if not reason:
                    reason =  self.env['return.order.reason'].create({'name':transaction.get('TSAReasonforReturnHeader','')})
            elif transaction.get('TSAREASONFORREPLACEMENT',''):
                reason = self.env['return.order.reason'].search(
                    [('name', '=', transaction.get('TSAREASONFORREPLACEMENT', ''))], limit=1)
                if not reason:
                    reason = self.env['return.order.reason'].create(
                        {'name': transaction.get('TSAREASONFORREPLACEMENT', '')})

            product = product_product.search([('default_code', '=', P_ExternalId)], limit=1)
            if not product:
                itmes_uri = item.get('URI')
                item_data = pepperi_account.get_data_by_uri(params={}, data={}, uri=itmes_uri)
                p_data = product_product._prepare_product_data(item_data)
                product = product_product.create(p_data)
                if automatic:
                    self.env.cr.commit()
            ModificationDateTime = datetime.datetime.strptime(line.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
            line_data += [(0, 0, {

                            'product_id': product and product.id,
                            'price': line.get('UnitPriceAfterDiscount'),
                            'modification_datetime': line.get('ModificationDateTime'),
                            'from_pepperi': True,
                            'reason':reason.id
                        })]
        return line_data

    def _prepare_order_data(self, pepperi_account, automatic, transactions):
        transactions_data = []
        ReaPartner = self.env['res.partner']
        
        AccountPaymentTerm = self.env['account.payment.term']
        Pricelist = self.env['product.pricelist']
        for item in transactions:
            ModificationDateTime = datetime.datetime.strptime(item.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
            DeliveryDate = datetime.datetime.strptime(item.get('DeliveryDate'), PEPPERI_DATE_Z)
            ActionDateTime = datetime.datetime.strptime(item.get('ActionDateTime'), PEPPERI_DATETIME_TZ)
            if 'TSAPayTerms' in item and item.get('TSAPayTerms'):
                AccountPaymentTerm = AccountPaymentTerm.search(['|','|', '|',  ('name', '=', item.get('TSAPayTerms')),('pepperi_name', '=', item.get('TSAPayTerms')),('pepperi_name', '=', item.get('TSAPayTermCode')),('name', '=', item.get('TSAPayTermCode'))], limit=1)
                if not AccountPaymentTerm:
                    AccountPaymentTerm = AccountPaymentTerm.search(['|',  ('name', '=', item.get('AccountTSAACCPayment')),('pepperi_name', '=', item.get('AccountTSAACCPayment'))], limit=1)
                if not AccountPaymentTerm:
                    AccountPaymentTerm = AccountPaymentTerm.create({'name': item.get('TSAPayTerms')})
            if 'TSAPLName' in item and item.get('TSAPLName'):
                Pricelist = Pricelist.search(['|', ('name', '=', item.get('TSAPLName')), ('pepperi_name', '=', item.get('TSAPLName'))], limit=1)

            BillTo = {
                    'street': item.get('BillToStreet'),
                    'city': item.get('BillToCity'),
                    'state_code': item.get('BillToState'),
                    'zip_code': item.get('BillToZipCode'),
                    'country_code': item.get('BillToCountry'),
                    'phone': item.get('BillToPhone'), 
                    'ModificationDateTime': item.get('ModificationDateTime'),
                    'property_payment_term_id': AccountPaymentTerm and AccountPaymentTerm.id,
                    'email':item.get('AccountTSAEmailOrder','') or item.get('AccountTSAACCEmail',''),
                    'l10n_it_codice_fiscale':item.get('AccountTSAACCCF',''),
                    'l10n_it_pa_index':item.get('AccountTSASDI',''),
                    'property_product_pricelist':Pricelist.id
                }
            ShipTo = {
                    'street': item.get('ShipToStreet'),
                    'city': item.get('ShipToCity'),
                    'state_code': item.get('ShipToState'),
                    'zip_code': item.get('ShipToZipCode'),
                    'country_code': item.get('ShipToCountry'),
                    'phone': item.get('ShipToPhone'),
                    'ModificationDateTime': item.get('ModificationDateTime'),
                    'property_payment_term_id': AccountPaymentTerm and AccountPaymentTerm.id,
                    'filemaker_code':item.get('ShipToExternalID'),
                    'email':item.get('AccountTSAEmailOrder','')
                }
            partner_invoice = ReaPartner._get_partner(name=item.get('BillToName'), item=BillTo, type='contact', company_type='company',filemaker_code=item.get('ShipToExternalID',False))
            partmer_ship = ReaPartner._get_partner(name=item.get('ShipToName'), item=ShipTo, type='delivery',parent_id=partner_invoice.id)
            if not Pricelist:
                Pricelist = partner_invoice.commercial_partner_id.property_product_pricelist
            if not Pricelist:
                Pricelist = pepperi_account.default_pricelist_id
            utm_name = pepperi_account.name
            utm_source = self.env['utm.source'].search([('name', '=', utm_name)], limit=1)
            if not utm_source:
                utm_source = self.env['utm.source'].create({'name': utm_name})
            agent_data = item['Agent']['Data']
            agent_id = ReaPartner
            if agent_data.get('Email',False):
                agent_id = ReaPartner.search([('email','=',agent_data.get('Email')),('fm_type','=','AGE')],limit=1)
                if not agent_id:
                    agent_id = ReaPartner.create({
                                                  'name':"%s %s" % (agent_data.get('FirstName',''),agent_data.get('LastName','')),
                                                  'email':agent_data.get('Email')
                                                  })
            transactions_data.append({
                    'partner_id': partner_invoice and partner_invoice.id,
                    'partner_invoice_id': partner_invoice and partner_invoice.id,
                    'partner_shipping_id': partmer_ship and partmer_ship.id,
                    'doc_cliente': item.get('InternalID'),
                    'notes': item.get('Remark'),
                    'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'modification_datetime': item.get('ModificationDateTime'),
                    'from_pepperi': True,
                    'return_order_line_ids': self._prepare_order_line_data(pepperi_account, automatic, item['TransactionLines']['Data'],item),
                    'pepperi_status': str(item.get('Status', '2')),
                    'state': 'sent',
                    'salesman_partner_id':agent_id.id,
                    'pricelist_id':Pricelist.id,
                    'pepperi_type':item.get('Type'),
                    'return_type':'replacement' if item.get('Type')=='Replacement' else 'refund'
                })
        return transactions_data

    def _get_item_params(self,peppery_account=False):
        
        params = {
            'where': "(Type='Replacement' OR Type='Credit Note') AND StatusName='Submitted' ",
            'order_by': 'InternalID,ModificationDateTime'
        }
        if peppery_account and peppery_account.last_return_synch_date:
            params['where'] = params.get('where') + " AND ModificationDateTime>'%s' AND CreationDateTime>'2022-01-01T00:00:00Z'" % peppery_account.last_return_synch_date.strftime(PEPPERI_DATETIME_TZ)
        return params

    # def _create_or_write_orders(self, orders):
    #     # we can use when we will use callback URL on pepperi
    #     SaleOrder = self.env['sale.order']
    #     mulit_order = []
    #     for order in orders:
    #         sale_order = SaleOrder.search([('origin', '=',  order.get('origin')), ('state', 'in', ['sent'])], limit=1)
    #         if not sale_order:
    #             mulit_order.append(order)
    #     SaleOrder = SaleOrder.create(mulit_order)
    #     return SaleOrder
    #
    #
    # def _cron_sync_pepperi_specific_sale_order_for_lines(self, automatic=False, pepperi_account=False,page=1):
    #
    #     for a in self:
    #         transactions = {}
    #         if not pepperi_account:
    #             pepperi_account = self.env['pepperi.account']._get_connection()
    #         if not pepperi_account:
    #             _logger.info('No Pepperi Account Found')
    #             return True
    #
    #         try:
    #             if automatic:
    #                 cr = registry(self._cr.dbname).cursor()
    #                 self = self.with_env(self.env(cr=cr))
    #
    #             trans = self._get_pepperi_transaction_by_id(pepperi_account, params={}, data={})
    #             if not trans:
    #                 return
    #             TransactionLinesURI = trans['TransactionLines']['URI']
    #             order_line_data_total = []
    #             pageCount = page
    #             order_line_data = pepperi_account.get_data_by_uri(params={'page':pageCount}, data={}, uri=TransactionLinesURI)
    #             while order_line_data:
    #                 order_line_data_total += order_line_data
    #                 pageCount +=1
    #                 order_line_data = pepperi_account.get_data_by_uri(params={'page':pageCount}, data={}, uri=TransactionLinesURI)
    #
    #             trans['TransactionLines']['Data'] = order_line_data_total
    #             orders_data ={
    #                 'order_line': self._prepare_order_line_data(pepperi_account, automatic, trans['TransactionLines']['Data']),
    #             }
    #
    #             # TODO: create multiple records at once? create_multi?
    #             # self._create_or_write_orders(orders_data)
    #             previousstate = self.state
    #             self.state = 'sent'
    #             self.write(orders_data)
    #             self.state = previousstate
    #             if automatic:
    #                 self.env.cr.commit()
    #
    #             pepperi_account.last_order_synch_date = fields.Datetime.now()
    #         except Exception as e:
    #             if automatic:
    #                 self.env.cr.rollback()
    #             _logger.error("%s"%(str(e)),exc_info=True)
    #             _logger.info('Sale Order synchronization response from pepperi ::: {}'.format(transactions))
    #             pepperi_account._log_message(str(e), _("Pepperi : Sale Order synchronization issues."), level="info", path="/transactions", func="_cron_sync_pepperi_sale_order")
    #             self.env.cr.commit()
    #         finally:
    #             if automatic:
    #                 try:
    #                     self._cr.close()
    #                 except Exception:
    #                     pass
    #         return True
    #
    @api.model
    def _cron_sync_pepperi_return_order(self, automatic=False, pepperi_account=False):
        transactions = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))

            params = self._get_item_params(pepperi_account)
            transactions = self._get_pepperi_transaction(pepperi_account, params=params, data={})
            for trans in transactions:
                TransactionLinesURI = trans['TransactionLines']['URI']
                order_line_data_total = []
                pageCount = 1
                order_line_data = pepperi_account.get_data_by_uri(params={'page':pageCount}, data={}, uri=TransactionLinesURI)
                while order_line_data:
                    order_line_data_total += order_line_data
                    pageCount +=1
                    order_line_data = pepperi_account.get_data_by_uri(params={'page':pageCount}, data={}, uri=TransactionLinesURI)
                
                trans['TransactionLines']['Data'] = order_line_data_total
                AccountURI = trans['Account']['URI']
                order_line_data = pepperi_account.get_data_by_uri(params={}, data={}, uri=AccountURI)
                trans['Account']['Data'] = order_line_data
                AgentURI = trans['Agent']['URI']
                order_line_data = pepperi_account.get_data_by_uri(params={}, data={}, uri=AgentURI)
                trans['Agent']['Data'] = order_line_data
            orders_data = self._prepare_order_data(pepperi_account, automatic, transactions)
            # TODO: create multiple records at once? create_multi?
            # self._create_or_write_orders(orders_data)
            ReturnOrder = self.env['return.order.sheet']
            orders_created = []
            for order in orders_data:
                return_order = ReturnOrder.search([('doc_cliente', '=',  order.get('doc_cliente'))], limit=1)
                if not return_order and order.get('doc_cliente') not in orders_created:
                    ReturnOrder.create(order)
                    orders_created.append(order.get('doc_cliente'))
                if automatic:
                    self.env.cr.commit()
            
            pepperi_account.last_return_synch_date = fields.Datetime.now()
        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            _logger.info('Return Order synchronization response from pepperi ::: {}'.format(transactions))
            pepperi_account._log_message(str(e), _("Pepperi : Sale Order synchronization issues."), level="info", path="/transactions", func="_cron_sync_pepperi_sale_order")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    # @api.model
    # def _cron_sync_post_pepperi_sale_order(self, automatic=False, pepperi_account=False):
    #     data = {}
    #     if not pepperi_account:
    #         pepperi_account = self.env['pepperi.account']._get_connection()
    #     if not pepperi_account:
    #         _logger.info('No Pepperi Account Found')
    #         return True
    #
    #     try:
    #         if automatic:
    #             cr = registry(self._cr.dbname).cursor()
    #             self = self.with_env(self.env(cr=cr))
    #         _logger.info('Start sync order status to pepperi')
    #         orders = self.env['sale.order'].search([('state','in',('sent', 'sale')),('from_pepperi','!=',False),('origin','!=',False),('pepperi_status' ,'!=','7')])
    #         for rec in orders:
    #             data = rec.get_order_pepperi_status()
    #             if bool(data):
    #                 data = self._post_pepperi_transaction(pepperi_account, params={}, data=data)
    #                 _logger.info('Align on Pepperi order %s'%rec.name)
    #                 if 'Status' in data:
    #                     ModificationDateTime = datetime.datetime.strptime(data.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
    #                     rec.write({
    #                             'pepperi_status': str(data.get('Status')),
    #                             'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    #                             'modification_datetime': data.get('ModificationDateTime'),
    #                         })
    #                     rec.message_post(body=_("TSATrackingNumber: %s" % data.get('TSATrackingNumber')))
    #                     if automatic:
    #                         self.env.cr.commit()
    #     except Exception as e:
    #         if automatic:
    #             self.env.cr.rollback()
    #         _logger.info(str(e))
    #         _logger.info('Post Sale Order synchronization response from pepperi ::: {}'.format(data))
    #         pepperi_account._log_message(str(e), _("Pepperi : Post Sale Order synchronization issues."), level="info", path="/transactions", func="_cron_sync_post_pepperi_sale_order")
    #         self.env.cr.commit()
    #     finally:
    #         if automatic:
    #             try:
    #                 self._cr.close()
    #             except Exception:
    #                 pass
    #     return True

    # ---------------------
    # Pepperi Models methods
    # ---------------------
    def _get_pepperi_transaction_by_id(self,pepperi_account, params={}, data={}):
        
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/transactions/%s'%(self.origin),
            params=params, data=data)
        return content
    
    def _get_pepperi_transaction(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of transactions including details about each transaction and its nested objects.
            Type: 'Sale Order'
            Ex:
                [
                    {
  "InternalID": 100564587,
  "UUID": "fd6187a4-c129-4b98-91ed-9aa6e98bd9df",
  "ExternalID": "100564587",
  "AccountTSAACCAddress": "VIALE BIDENTE 39",
  "AccountTSAACCBank": "CASSA RISPARMI PARMA E PIACENZA",
  "AccountTSAACCCF": "02142300405",
  "AccountTSAACCCity": "FORL�",
  "AccountTSAACCCompanyName": "OREFICERIA RANIERI RANIERO SNC",
  "AccountTSAACCCountry": "ITALIA",
  "AccountTSAACCEmail": "Oreficeria.ranieri@gmail.com",
  "AccountTSAACCIBAN": "IT20M0623013226000056767742",
  "AccountTSAACCPayment": "BONIFICO 30/60/90 GG F.M. (BANK TRANSFER 30/60/90 DAYS)",
  "AccountTSAACCPhone": "0543/780300",
  "AccountTSAACCPV": "FORLI",
  "AccountTSAACCZipCode": "47121",
  "AccountTSAEmailOrder": "oreficeria.ranieri@gmail.com",
  "AccountTSALinkScadenzarioPDF": "https://milor-view.thron.com/api/xcontents/resources/delivery/getThumbnail/milor/0x0/00005515",
  "AccountTSAPhone2": "0543780300",
  "ActionDateTime": "2020-07-17T10:53:13Z",
  "ActivityTypeID": 154745,
  "Archive": false,
  "BillToCity": "FORLI'",
  "BillToCountry": "Italy",
  "BillToFax": "",
  "BillToName": "RANIERI",
  "BillToPhone": "0543780300",
  "BillToState": "",
  "BillToStreet": "Viale Bidente 39",
  "BillToZipCode": "47121",
  "CreationDateTime": "2020-07-17T10:48:51Z",
  "CurrencySymbol": "EUR",
  "DeliveryDate": "2020-07-17Z",
  "DiscountPercentage": 0,
  "GrandTotal": 293.2,
  "Hidden": false,
  "ItemsCount": 4,
  "ModificationDateTime": "2020-07-20T10:10:41Z",
  "QuantitiesTotal": 5,
  "Remark": "Spedire tassativamente il 3 o il 4 agosto",
  "ShipToCity": "FORLI'",
  "ShipToCountry": "Italy",
  "ShipToExternalID": "00005515",
  "ShipToFax": "",
  "ShipToName": "RANIERI",
  "ShipToPhone": "0543780300",
  "ShipToState": "",
  "ShipToStreet": "Viale Bidente 39",
  "ShipToZipCode": "47121",
  "Signature": {},
  "Status": 16,
  "StatusName": "InPlanning",
  "SubmissionGeoCodeLAT": 0,
  "SubmissionGeoCodeLNG": 0,
  "SubTotal": 293.2,
  "SubTotalAfterItemsDiscount": 293.2,
  "TaxPercentage": 22,
  "TSAACCCountryISO": "",
  "TSAACCCountryNew": "",
  "TSABrand": null,
  "TSABuyerRemark": null,
  "TSACheckIfRevised": null,
  "TSACreditNoteStatus": null,
  "TSACurrency": "EUR",
  "TSADateInvoice": null,
  "TSADateProposal": null,
  "TSAGovernmentID": "02142300405",
  "TSAInvoiceNumber": null,
  "TSALinkTracking": null,
  "TSANr": null,
  "TSAOrderStatus": null,
  "TSAPackagingImplicito": "YES",
  "TSAPayTermCode": "004",
  "TSAPayTerms": "RI.BA. 30 GG F.M. (LCR SDD 30 DAYS)",
  "TSAPLName": "EURO 2.2",
  "TSAProposalTitle": null,
  "TSAQtyMissingHeader": null,
  "TSARagioneSociale": null,
  "TSAReason": null,
  "TSAREASONFORREPLACEMENT": null,
  "TSAReasonforReturnHeader": null,
  "TSARemarkMilor": null,
  "TSAResponse": null,
  "TSAResponse2": null,
  "TSAReturnStatus": null,
  "TSAShippedBy": null,
  "TSAShippingAgent": null,
  "TSAShow": null,
  "TSATotalPriceSum": null,
  "TSATotWeight": null,
  "TSATrackingNumber": null,
  "TSAType": null,
  "TSAUser": null,
  "TSAWeeklyClosing": null,
  "Type": "Sales Order",
  "Account": {
    "Data": {
      "InternalID": 20030609,
      "UUID": "803744fc-7656-4282-b8c9-09087deaaa73",
      "ExternalID": "00005515"
    },
    "URI": "/accounts/20030609"
  },
  "AdditionalAccount": {
    "Data": {
      "InternalID": 20030609,
      "UUID": "803744fc-7656-4282-b8c9-09087deaaa73",
      "ExternalID": "00005515"
    },
    "URI": "/accounts/20030609"
  },
  "Agent": {
    "Data": {
      "InternalID": 10255605,
      "UUID": "febf2c00-36bd-4de0-a046-b80a0cec34a8",
      "ExternalID": "184"
    },
    "URI": "/users/10255605"
  },
  "Catalog": {
    "Data": {
      "InternalID": 60335,
      "UUID": "80ca87da-f3e5-4260-8b17-13e6292f23c6",
      "ExternalID": "Items in Collection"
    },
    "URI": "/catalogs/60335"
  },
  "ContactPerson": null,
  "Creator": {
    "Data": {
      "InternalID": 10255605,
      "UUID": "febf2c00-36bd-4de0-a046-b80a0cec34a8",
      "ExternalID": "184"
    },
    "URI": "/users/10255605"
  },
  "OriginAccount": null,
  "TransactionLines": {
    "Data": [
      {
        "InternalID": 936354771,
        "CreationDateTime": "2020-07-17T10:50:02Z",
        "DeliveryDate": "2020-07-17Z",
        "ItemExternalID": "WSOX00366.RUBY-16",
        "ItemName": "",
        "LineNumber": 0,
        "TotalUnitsPriceAfterDiscount": 58.64,
        "TotalUnitsPriceBeforeDiscount": 58.64,
        "UnitDiscountPercentage": 0,
        "UnitPrice": 58.64,
        "UnitPriceAfterDiscount": 58.64,
        "UnitsQuantity": 1
      },
      {
        "InternalID": 936354772,
        "CreationDateTime": "2020-07-17T10:50:00Z",
        "DeliveryDate": "2020-07-17Z",
        "ItemExternalID": "WSOX00366.RUBY-18",
        "ItemName": "",
        "LineNumber": 0,
        "TotalUnitsPriceAfterDiscount": 58.64,
        "TotalUnitsPriceBeforeDiscount": 58.64,
        "UnitDiscountPercentage": 0,
        "UnitPrice": 58.64,
        "UnitPriceAfterDiscount": 58.64,
        "UnitsQuantity": 1
      },
      {
        "InternalID": 936354773,
        "CreationDateTime": "2020-07-17T10:49:39Z",
        "DeliveryDate": "2020-07-17Z",
        "ItemExternalID": "WSOX00366.SAP-16",
        "ItemName": "",
        "LineNumber": 0,
        "TotalUnitsPriceAfterDiscount": 58.64,
        "TotalUnitsPriceBeforeDiscount": 58.64,
        "UnitDiscountPercentage": 0,
        "UnitPrice": 58.64,
        "UnitPriceAfterDiscount": 58.64,
        "UnitsQuantity": 1
      },
      {
        "InternalID": 936354774,
        "CreationDateTime": "2020-07-17T10:49:34Z",
        "DeliveryDate": "2020-07-17Z",
        "ItemExternalID": "WSOX00366.SAP-14",
        "ItemName": "",
        "LineNumber": 0,
        "TotalUnitsPriceAfterDiscount": 117.28,
        "TotalUnitsPriceBeforeDiscount": 117.28,
        "UnitDiscountPercentage": 0,
        "UnitPrice": 58.64,
        "UnitPriceAfterDiscount": 58.64,
        "UnitsQuantity": 2
      }
    ],
    "URI": "/transaction_lines?where=TransactionInternalID=100564587"
  }
},
                ]"""
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/transactions',
            params=params, data=data)
        return content

    def _post_pepperi_transaction(self, pepperi_account, params={}, data={}):
        """
            data = {
                    "InternalID": 95844740,
                    "Status": 16,
                }
        """
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        content = pepperi_account._synch_with_pepperi(
            http_method='POST', service_endpoint='/transactions',
            params=params, data=data)
        return content


class SaleOrderLine(models.Model):
    _name = 'return.order.line'
    _inherit = ['return.order.line', 'pepperi.mixin']

    def _get_pepperi_transaction_line(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of transactions including details about each transaction and its nested objects.
            Type: 'Sale Order'
            Ex:
                [
                    {
                        "InternalID": 889966682,
                        "Archive": false,
                        "CreationDateTime": "2020-05-06T19:27:39Z",
                        "DeliveryDate": "2020-05-06Z",
                        "Hidden": false,
                        "LineNumber": 0,
                        "ModificationDateTime": "2020-05-06T19:28:39Z",
                        "UnitDiscountPercentage": 0,
                        "UnitPrice": 0,
                        "UnitsQuantity": 4,
                        "Item": {
                            "Data": {
                                "InternalID": 57598609,
                                "UUID": "81e03410-a94f-4bba-8632-7088bbd09910",
                                "ExternalID": "12346"
                            },
                        "URI": "/items/57598609"
                        },
                        "Transaction": {
                            "Data": {
                                "InternalID": 95267603,
                                "UUID": "22a68cce-d612-49d5-ba41-57ee49718bff",
                                "ExternalID": null
                            },
                        "URI": "/transactions/95267603"
                        }
                    },
                ]"""
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/transaction_lines',
            params=params, data=data)
        return content
