# -*- coding: utf-8 -*-
# © 2021 Rapsodoo, Roberto Zanardo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError

class PickingCustomTracking(models.Model):
    _inherit = "stock.picking"
    
    custom_tracking = fields.Char(string='Custom tracking', 
                                compute='_compute_custom_tracking',
                                search='_search_custom_tracking',)

    def _compute_custom_tracking(self):
        for pick in self:
            if pick.carrier_id.name=='GLS ITALIA':
                pick.custom_tracking = str(pick.carrier_tracking_ref)
            else:
                pick.custom_tracking = None

    #Forziamo la ricerca per escludere spedizionier non GLS
    def _search_custom_tracking(self, operator, value):
        new_value = value[2:11]
        picking_ids = self.search(
            ['|', ('carrier_tracking_ref', operator, new_value), ('carrier_tracking_ref', operator, value),
             ('delivery_partner_id.name', '=', 'GENERAL LOGISTIC SYSTEMS MILANO S.R.L.')])
        return [('id', 'in', picking_ids.ids)]




