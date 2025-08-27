from odoo import fields, models, api


class NaApiSyncConfigActions(models.Model):
    _name = 'na.api.sync.config.actions'

    config_id = fields.Many2one('na.api.sync.config', string='Configuration', required=True,
                                ondelete='cascade')
    model_id = fields.Many2one('ir.model', related='config_id.model_id')
    name = fields.Char(string='Action Tag', help='Tag to identify the action'
                                                 ' when called via XML-RPC', required=True)
    action_id = fields.Many2one('ir.actions.server', string='Odoo Action', required=True,
                                domain="[('model_id', '=', model_id)]")

    _sql_constraints = [
        ('check_name', 'UNIQUE (name, config_id)', 'This Action Tag already exists.')
    ]

    # Name cannot have spaces
    @api.onchange('name')
    def _remove_space_name(self):
        for rec in self:
            if rec.name:
                rec.name = rec.name.replace(" ", "").replace("\n", "")
