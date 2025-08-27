from odoo import fields, models, api


class ManualImportJSONWizard(models.TransientModel):
    _name = 'na.api.sync.manual.import.json.wiz'
    _description = 'Manual Import JSON Wizard'

    config_id = fields.Many2one('na.api.sync.config', string='Configuration', required=True)
    json_to_imp = fields.Text(string="JSON to Import", help='You can only import one record', required=True)
    action_tag = fields.Char(string='Action Tag')

    def import_json(self):
        # FIXME: Importa un record alla volta, prende solo quelli GET
        api_fields = self.config_id.api_fields_ids.filtered(
            lambda f: not f.exclusive_use or f.exclusive_use == 'get')
        odoo_rec = self.config_id.import_record(self.json_to_imp, api_fields)
        odoo_action = self.config_id.api_actions_ids.filtered(
            lambda a: a.name == self.action_tag)
        if odoo_action:
            odoo_action.action_id.with_context(active_id=odoo_rec.id,
                                               active_ids=[odoo_rec.id],
                                               active_model=self.config_id.model_id.model).run()
