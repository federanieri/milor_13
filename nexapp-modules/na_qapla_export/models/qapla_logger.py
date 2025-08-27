# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api
import odoo
from odoo import SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta


class QaplaLogger(models.Model):
    _name = 'qapla.logger'
    _order = 'create_date DESC'

    name = fields.Char(string='Name')
    try_date = fields.Datetime(string='Attempt Date')
    logger_information = fields.Html(string='Logger Information')
    error = fields.Boolean(string='Error', default=False)

    def create_log(self, name, text='', error=False):
        registry = odoo.registry(self.env.cr.dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            log = env['qapla.logger'].create({
                'name': name,
                'try_date': datetime.today(),
                'logger_information': text,
                'error': error,
            })
        return log

