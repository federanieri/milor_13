from odoo import models, fields

class NaConfirmationMessage(models.TransientModel):
    _name = "na.confirmation.message"

    message = fields.Text(string="Conferma ordine")
    confirm_no_action = fields.Boolean(default=False)

    def sale_action_confirm(self):
        sale_order_id = self.env.context.get('active_id')
        return self.env['sale.order'].search([('id', '=', sale_order_id)]).action_confirm()

    def sale_action_confirm_no_action(self):
        sale_order_id = self.env.context.get('active_id')
        return self.env['sale.order'].search([('id', '=', sale_order_id)]).confirm_without_action()
