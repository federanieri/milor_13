# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import datetime

from odoo import api, fields, models, registry, _
from odoo.tools import  DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

PEPPERI_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'pepperi.mixin']
    
    pepperi_payment_terms = fields.Char(string='TERMINI DI PAGAMENTO')
    pepperi_pricelist = fields.Char(string='Pepperi Pricelist')
    pepperi_agent = fields.Char(string='AGENTE')
    pepperi_iban = fields.Char(string='IBAN')
    pepperi_country = fields.Char(string='Pepperi Country')


    @api.model
    def get_domain_contact(self,name,item):
        domain = []
        domain.append(('name','=',name))
        return domain
    
    @api.model
    def get_domain_shipto(self,item,parent_id):
        domain = []
        domain.append(('parent_id','=',parent_id))
        domain.append('|')
        domain.append(('filemaker_code','=',item.get('filemaker_code')))
        domain.append('&')
        domain.append('&')
        domain.append(('street','=',item.get('street')))
        domain.append(('zip','=',item.get('zip_code')))
        domain.append(('city','=',item.get('city')))                        
        return domain
        
    def _get_partner(self, name, item={}, type='contact', company_type='person', parent_id=False,filemaker_code=False):
        """
            name: contact name,
            item: {
                    'street': '',
                    'city': '',
                    'state_code': '',
                    'zip_code': '',
                    'country_code': '',
                    'phone': '',
                    'mobile': '',
                    'email': '',
                    'InternalId': '',
                    'ExternalId': '',
                    'ModificationDateTime': '',
                }
        """

        data = {
            'from_pepperi': True
            
            }
        res_partner = self.env['res.partner']
        if 'ModificationDateTime' in item and item.get('ModificationDateTime'):
            ModificationDateTime = datetime.datetime.strptime(item.get('ModificationDateTime'), PEPPERI_DATETIME_TZ)
            data.update({
                    'last_update_from_pepperi': ModificationDateTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'modification_datetime': item.get('ModificationDateTime')
                })
        
        try:
            if filemaker_code:
                last = filemaker_code[-1]
                if len(filemaker_code)==9 and last.isalpha():
                    filemaker_code = str(int(filemaker_code[0:-1]))
                    filemaker_string = '%s%s'%('CL',filemaker_code)
                elif filemaker_code.isnumeric():
                    filemaker_code = str(int(filemaker_code))
                    filemaker_string = '%s%s'%('CL',filemaker_code)
                else:
                    filemaker_string = filemaker_code
                res_partner = res_partner.search([('fm_code','=',filemaker_string)], limit=1)
        except Exception as e:
            _logger.error("%s"%(str(e)),exc_info=True)
            
        if not res_partner:
            if type=='contact':
                domain = self.get_domain_contact(name,item)
            else:
                domain = self.get_domain_shipto(item,parent_id)
            if 'InternalId' in item and item.get('InternalId'):
                domain = [('ref', '=', item.get('InternalId'))]
            
            res_partner = res_partner.search(domain, limit=1)

        country = item.get('country_code', '').strip()
        country_id = self.env['res.country'].search([('name', '=ilike', country)], limit=1)
        state = item.get('state_code', '').strip()
        state_id = False
        if not country_id:
            country_id = self.env['res.country'].with_context(lang='en').search([('name', '=ilike', country)], limit=1)
        if not country_id and parent_id:
            parent_partner_id = self.env['res.partner'].browse(parent_id)
            country_id = parent_partner_id.country_id
        if country_id:
            state_id = self.env['res.country.state'].search([('country_id', '=', country_id.id),('name', '=ilike', state)], limit=1)

        if not res_partner:
            data.update({
                'name': name,
                'type': type,
                'company_type': company_type,
                'parent_id': parent_id,
                'filemaker_code':item.get('filemaker_code', False),
                'street': item.get('street', ''),
                'city': item.get('city', ''),
                'state_id': state_id and state_id.id,
                'zip': item.get('zip_code', ''),
                'country_id': country_id and country_id.id,
                'mobile': item.get('mobile', ''),
                'phone': item.get('phone', ''),
                'email': item.get('email', ''),
                'ref': item.get('InternalId', ''),
                'property_payment_term_id': item.get('property_payment_term_id'),
                'property_product_pricelist':item.get('property_product_pricelist'),

                'pepperi_payment_terms': item.get('pepperi_payment_terms'),
                'pepperi_iban': item.get('pepperi_iban'),
                'pepperi_country': item.get('country_code', ''),
                'pepperi_pricelist': item.get('pepperi_pricelist',''),
                'salesman_partner_id': item.get('salesman_partner_id'),
                'pepperi_agent': item.get('pepperi_agent', ''),
            })
            if len(item.get('l10n_it_codice_fiscale',''))>=11 :
                data.update({
                             'l10n_it_codice_fiscale':item.get('l10n_it_codice_fiscale','')
                             
                             })
            if len(item.get('l10n_it_pa_index',''))>=6:
                data.update({
                             'l10n_it_pa_index':item.get('l10n_it_pa_index','')
                             })
            if not item.get('email', '') and parent_id:
                parent_partner_id = self.env['res.partner'].browse(parent_id)
                data.update({
                    'email':parent_partner_id.email
                    })
        if item.get('email', '') and not res_partner.email:
            data.update({
                         'email': item.get('email', '')
                         })
        data.update({
            'filemaker_code':item.get('filemaker_code', False),      
            'ref': item.get('InternalId', False)
            })
    
        if not res_partner:
            res_partner = res_partner.create(data)
        else:
            if parent_id:
                parent_partner_id = self.env['res.partner'].browse(parent_id)
                if not res_partner.country_id:
                    data.update({
                                 'country_id':parent_partner_id.country_id.id
                                 })
                if not res_partner.email:
                    data.update({
                                 'email':parent_partner_id.email
                                 })
            # Added by Nayan (Update Contact Data)
            data.update({

                'street': item.get('street'),
                'city': item.get('city'),
                'state_id': state_id and state_id.id,
                'zip': item.get('zip_code', ''),
                'country_id': country_id and country_id.id or False,
                'mobile': item.get('mobile', ''),
                'phone': item.get('phone', ''),
                'email': item.get('email', ''),
                'pepperi_country': item.get('country_code', ''),
                'pepperi_payment_terms': item.get('pepperi_payment_terms'),
                'pepperi_iban': item.get('pepperi_iban'),
                'pepperi_pricelist': item.get('pepperi_pricelist', ''),
                'property_payment_term_id': item.get('property_payment_term_id') if not res_partner.property_payment_term_id else res_partner.property_payment_term_id.id,
                'property_product_pricelist': item.get('property_product_pricelist') if not res_partner.property_product_pricelist else res_partner.property_product_pricelist.id,
                'salesman_partner_id': item.get('salesman_partner_id') if not res_partner.salesman_partner_id else res_partner.salesman_partner_id.id,
                'pepperi_agent': item.get('pepperi_agent', ''),
            })
            # 2022/04/08 DPassera--Milor richiede di non aggiornare il contatto alla ricezione di un ordine
            # res_partner.write(data)
        return res_partner

    def _prepare_contacts_data(self, pepperi_items):
        for item in pepperi_items:
            pepperi_contact_account = self.get_pepperi_contact_account(item)
            contacts_data = {
                'name': item.get('FirstName') + item.get('LastName'),
                'phone': item.get('Phone'),
                'email': item.get('Email'),
                'mobile': item.get('Mobile'),
                'InternalId': item.get('InternalID'),
                'ExternalId': item.get('ExternalID'),
                'ModificationDateTime': item.get('ModificationDateTime'),

                'pepperi_payment_terms': pepperi_contact_account.get('TSAACCPayment') or False,
                'pepperi_iban': pepperi_contact_account.get('TSAACCIBAN') or False,
            }
            yield contacts_data

    def get_pepperi_contact_account(self,contact_response):
        pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True
        pepperi_contact_account_response = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint=contact_response.get('Account').get('URI'), data={})
        return pepperi_contact_account_response




    def _create_or_write_contacts(self, contacts):
        # we can use when we will use callback URL on pepperi
        ResPartner = self.env['res.partner']
        for partner in contacts:
            ResPartner |= self._get_partner(partner.get('name'), item=partner, type='contact', company_type='person', parent_id=False)
        return ResPartner

    def _get_item_params(self):
        partner = self.env['res.partner'].search([('last_update_from_pepperi', '!=', False)], limit=1, order="last_update_from_pepperi desc")
        params = {
            # 'page': 1,
            'page_size': 100,
        }
        if partner.modification_datetime:
            params.update({
                'where': "ModificationDateTime>'%s'" % partner.modification_datetime,
            })
        return params

    @api.model
    def _cron_sync_pepperi_contacts(self, automatic=False, pepperi_account=False):
        contacts = {}
        if not pepperi_account:
            pepperi_account = self.env['pepperi.account']._get_connection()
        if not pepperi_account:
            _logger.info('No Pepperi Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))

            params = self._get_item_params()
            contacts = self._get_pepperi_contacts(pepperi_account, params=params, data={})
            contacts_data = self._prepare_contacts_data(contacts)
            # TODO: create multiple records at once? create_multi?
            # self._create_or_write_contacts(contacts_data)
            ResPartner = self.env['res.partner']
            for partner in contacts_data:
                ResPartner |= self._get_partner(partner.get('name'), item=partner, type='contact', company_type='person', parent_id=False)
                if automatic:
                    self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            _logger.info('Contacts synchronization response from pepperi ::: {}'.format(contacts))
            pepperi_account._log_message(str(e), _("Pepperi : Contacts synchronization issues."), level="info", path="/contacts", func="_cron_sync_pepperi_sale_order")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    # ---------------------
    # Pepperi Models methods
    # ---------------------

    def _get_pepperi_contacts(self, pepperi_account, params={}, data={}):
        """
            Retrieves a list of contacts including details about each contact and its nested objects.
            Ex:
                [
                    {
                        "InternalID": 11540111,
                        "UUID": "28861cb9-7c33-414c-bdee-8f7a985f2e29",
                        "ExternalID": "odooperppri",
                        "CreationDateTime": "2020-05-19T06:37:38Z",
                        "Email": "odooperppri@test.com",
                        "Email2": "",
                        "FirstName": "odooperppri",
                        "Hidden": false,
                        "IsBuyer": false,
                        "LastName": "odooperppri",
                        "Mobile": "123456780",
                        "ModificationDateTime": "2020-05-19T06:37:38Z",
                        "Phone": "1234567890",
                        "Role": "consultant",
                        "Status": 2,
                        "TypeDefinitionID": 268933,
                        "Account": {
                          "Data": {
                            "InternalID": 20523975,
                            "UUID": "04d5a970-e308-456a-a2a7-4aa690451446",
                            "ExternalID": ""
                          },
                          "URI": "/accounts/20523975"
                        },
                        "Profile": null
                    }
                ]"""
        content = pepperi_account._synch_with_pepperi(
            http_method='GET', service_endpoint='/contacts',
            params=params, data=data)
        return content
