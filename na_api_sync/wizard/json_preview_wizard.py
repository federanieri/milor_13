from odoo import fields, models, api

import json


class JSONPreviewWizard(models.TransientModel):
    _name = 'na.api.sync.json.preview.wiz'
    _description = 'JSON Preview Wizard'

    config_id = fields.Many2one('na.api.sync.config', string='Configuration', required=True)
    rec_id = fields.Reference(selection='_selection_target_model', string='Odoo Record',
                              required=True)
    api_preview = fields.Text(string="JSON Preview", compute='_compute_api_preview')

    @api.depends('config_id', 'rec_id')
    def _compute_api_preview(self):
        # TODO: Esplicitare da qualche parte che non ci sono i campi GET
        for rec in self:
            if rec.rec_id:
                api_fields = rec.config_id.api_fields_ids.filtered(
                    lambda f: not f.exclusive_use or f.exclusive_use == 'post')
                rec.api_preview = json.dumps(rec.config_id.export_record(rec.rec_id, api_fields),
                                             ensure_ascii=False)
            else:
                rec.api_preview = ''

    @api.model
    def _selection_target_model(self):
        api_model = self.env.context.get('api_model')
        if api_model:
            odoo_model = self.env['ir.model'].sudo().search([('id', '=', api_model)])
            return [(odoo_model.model, odoo_model.name)]
        else:
            return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]
