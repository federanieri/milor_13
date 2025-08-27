from odoo import models, fields, api,_
import logging

_logger = logging.getLogger(__name__)

class wizardForceDone(models.TransientModel):
    _name = 'syd_os1.wizard_force_done'
    _description = "Wizard Force Done"
    
    doc_os1_id = fields.Many2one('syd_os1.doc_os1', string='DOC OS1')
    key = fields.Char('KTestaDoc', required=True)
    
    def startforceDone(self):
        self.doc_os1_id._setDone(self.key)