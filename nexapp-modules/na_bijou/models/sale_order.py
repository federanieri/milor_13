# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    client_mail = fields.Char(string="Client Email")
    source_id_name = fields.Char(related="source_id.name")
    bl_email = fields.Char(string='Email for BL')
