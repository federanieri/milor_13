from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'
    
    module_syd_cancel_ch_orders = fields.Boolean("Action Cancel Commercehub Order")
