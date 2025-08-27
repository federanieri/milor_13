from odoo import fields, models, api
from datetime import date, timedelta, datetime
class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def clean_onpage_attachment(self):
        days_delay = 15
        latest_date = date.today() - timedelta(days=days_delay)
        latest_date = datetime.combine(latest_date, datetime.min.time())
        records = self.env['ir.attachment'].search([('mimetype', '=', 'text/csv'),('description', '=', 'onpage_datas'),
                                                    ('create_date', '<', latest_date)])
        for record in records:
            record.unlink()
