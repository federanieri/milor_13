
from itertools import chain 

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang
from itertools import groupby
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit="sale.order"
    
    
    deactivate_configurator = fields.Boolean('Dactivate Configurator')