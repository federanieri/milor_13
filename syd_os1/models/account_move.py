# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    document_os1_line_id = fields.Many2one('syd_os1.doc_os1.line', string="DOC OS1 line")

class AccountMove(models.Model):
    _inherit = "account.move"
    
    temp_name = fields.Char('Name OS1 temp')
    amount_untaxed_signed = fields.Monetary(currency_field='currency_id')
    amount_tax_signed = fields.Monetary(currency_field='currency_id')
    amount_total_signed = fields.Monetary(currency_field='currency_id')
    amount_residual_signed = fields.Monetary(currency_field='currency_id')
    already_sent = fields.Boolean('Already sent')
    
    tot_document_euro = fields.Float('Totale documento euro')
    tot_document_net_euro = fields.Float('Totale imponibile documento euro')
    tot_vat_euro = fields.Float('Totale IVA euro')
    transport_costs_euro = fields.Float('Spese trasporto euro')
    miscellaneous_expenses_euro = fields.Float('Spese varie euro')
    packaging_costs_euro = fields.Float('Spese imballo euro')
    
    invoice_imported_from_os1 = fields.Boolean('invoice imported from os1')
    
    #Complete overwriting done because on OS1 there are invoices with different
    #invoice date but with the same name but Odoo throws an error if you have a similar situation
    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        for move_id in self:
            if not move_id.invoice_imported_from_os1:
                super(AccountMove, move_id)._check_unique_sequence_number()
    
    def action_post(self):
        ris = super(AccountMove, self).action_post()
        if bool(self.temp_name):
            self.write({'name':self.temp_name,
                        'temp_name':False})
        return ris
    
    def createPayment(self):
        vals = {'amount':self.amount_total,
                'currency_id':self.currency_id.id,
                'journal_id':self.env['account.journal'].search([('type','=','bank'),('company_id','=',self.env.company.id)], limit = 1),
                'payment_date':date.today(),
                'payment_type':'inbound' if self.amount_total > 0 else 'outbound',
                'invoice_ids':[[6,0,[self.id]]]}
        payment_id = self.env['account.payment'].create(vals)
        payment_id.post()
        return True
    
    def _check_before_xml_exporting(self):
        _logger.info('jump method')
    
    def invoice_generate_xml(self):
        _logger.info('jump method')