# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ReportAction(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('zpl', 'zpl')])

    @api.model
    def render_zpl(self, docids, data=None):
        # INFO: sets default data values.
        if not data:
            data = {}
        data.setdefault('report_type', 'text')

        data = self._get_rendering_context(docids, data)
        return self.render_template(self.report_name, data), 'text'
