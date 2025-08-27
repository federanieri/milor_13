from odoo import fields, models, api
from datetime import date

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals):
        dict_values = vals[0]
        # if 'discount' in dict_values:
        partner_id = self.env['sale.order'].search([('id', '=', dict_values['order_id'])]).partner_id
        for line in partner_id.discount_line:
            if line.discount_percentage > 0:
                discount_start = line.discount_start
                discount_end = line.discount_end
                today = date.today()
                if discount_start <= today <= discount_end:
                    dict_values['discount'] = line.discount_percentage
                    res = super(SaleOrderLine, self).create(vals)
                    return res
        res = super(SaleOrderLine, self).create(vals)
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm_message(self):
        return self.na_confirmation_message(False)

    def confirm_without_action_message(self):
        return self.na_confirmation_message(True)


    def na_confirmation_message(self, no_action):
        highest_discount = max(self.order_line.mapped('discount'))
        text = "Lo sconto più alto presente nell'ordine è del " + str(highest_discount) + "%"
        value = self.env['na.confirmation.message'].sudo().create({'message': text, 'confirm_no_action': no_action})
        action = self.env.ref('na_milor_discount.na_wizard_message_confirmation').read()[0]
        action['res_id'] = value.id
        return action

    def na_open_discount_wizard(self):
        action = self.env.ref('na_milor_discount.na_custom_discount_wizard').read()[0]
        action['context'] = {'active_ids': [order.id for order in self]}
        return action