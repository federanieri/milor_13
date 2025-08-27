# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class NaApiSyncLog(models.Model):
    _name = 'na.api.sync.log'
    _order = 'create_date DESC'

    env_id = fields.Many2one(string='Environment', required=True)
    config_id = fields.Many2one('na.api.sync.config', string='Synchronization', ondelete='cascade')
    method = fields.Selection([('get', 'GET'), ('post', 'POST')], string='Method')
    log_msg = fields.Text(string='Log')

    def _cron_delete_old_log(self):
        all_envs = self.env['na.api.sync.env'].search([])
        for env in all_envs:
            # if we don't have anything in log_days param we use the default value 7
            log_days = env.log_days
            limit_date = datetime.now() + relativedelta(days=-int(log_days))
            # if the logs have a creation date prior to the limit, we delete the records
            old_logs = self.env['na.api.sync.log'].search([('create_date', '<', limit_date),
                                                           ('env_id', '=', env.id)])
            old_logs.unlink()
