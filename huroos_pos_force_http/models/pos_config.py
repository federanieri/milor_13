from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _get_pos_base_url(self):
        return '/pos/web'

