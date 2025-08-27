import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.tools.safe_eval import safe_eval

class WizardReport(models.TransientModel):
    _name = "syd_report_wizard.wizard_report"
    _description = 'Wizard Report'
    
    quantity = fields.Integer('Quantity',default=1)
    report_id = fields.Many2one('ir.actions.report',string='Report',domain="[('model','=',model)]")
    model = fields.Char('Model')
    res_ids = fields.Char('Ids')
    
    
    
    def print_report(self):
        """
        To get the date and print the report
        @return : return report
        """
        ids = []
        for x in range(self.quantity):
            ids += self.res_ids.split(",")
        
        return self.report_id.report_action(ids)
    