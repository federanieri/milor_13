# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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
from odoo.osv import expression 




         
class Purchase(models.Model):
    _inherit = "purchase.order"
    
    published_in_portal = fields.Boolean('Published In Portal',default=True)
    
    def preview_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
        
        
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'PO - %s' % self.name
    
    