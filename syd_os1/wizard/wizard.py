from odoo import models, fields, api,_
import logging

_logger = logging.getLogger(__name__)

class wizardImportInvoice(models.TransientModel):
    _name = 'syd_os1.wizard_import_invoice'
    _description = "Wizard Force Invoice"
    
    doc_os1_ids = fields.Many2many('syd_os1.doc_os1', 'docos1_wizardimportinvoice_rel', string='DOC OS1')
    KTestaDoc = fields.Char('KTestaDoc', required=True)
    NumDocumento = fields.Char('NumDocumento', required=True)
    DataDocumento = fields.Date('DataDocumento', required=True)
    
    def startImportInvoice(self):
        self.doc_os1_ids._forceCreateInvoice(self.KTestaDoc, self.NumDocumento, self.DataDocumento)