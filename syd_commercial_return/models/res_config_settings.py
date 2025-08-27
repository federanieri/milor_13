from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    module_syd_compute_max_qty_crma = fields.Boolean("Check Qty CRMA in Invoice")
