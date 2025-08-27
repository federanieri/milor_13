# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import calendar
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_date
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    account_code_os1 = fields.Selection([
        ('milor_account_code', 'Codice Contabilità'),
        ('milor_account_code_id', 'Nuovo Codice Contabilità'),
        ], string='Account code OS1', readonly=False)