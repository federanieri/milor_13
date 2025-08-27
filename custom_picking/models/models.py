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
        for todo in self:
            todo.custom_tracking = str(todo.carrier_tracking_ref)

    def _search_custom_tracking(self, operator, value):
        #     M4610368748010BA
        #     610368748

        #da:  M4611282220010BA
        #a :  611282220
        new_value = value[2:11]
        #raise UserError(str(new_value))
        return [('carrier_tracking_ref', operator, new_value)]



