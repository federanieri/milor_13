from odoo import api, fields, models
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    one_size_attribute = fields.Many2one('product.attribute', string="Attributo per taglia unica")
    one_size_value = fields.Many2one('product.attribute.value', string="Valore attributo per taglia unica")
    size_attributes = fields.Many2many('product.attribute', 'res_config_settings_size_rel', string="Taglia")
    stone_attributes = fields.Many2many('product.attribute', 'res_config_settings_stone_rel', string="Pietra")
    plating_attributes = fields.Many2many('product.attribute', 'res_config_settings_plating_rel', string="Placcatura")
    path_onpage_attachments = fields.Char(string="Path allegati onpage")
    single_stock = fields.Boolean(string="Gestione giacenze singole")
    onpage_token = fields.Char(string="Token onpage anagrafica")
    onpage_token_qty = fields.Char(string="Token onpage giacenze")

    @api.onchange('one_size_attribute')
    def onchange_attribute(self):
        for rec in self:
            return {'domain': {'one_size_value': [('attribute_id', '=', rec.one_size_attribute.id)]}}

    @api.model
    def get_values(self):
        res = super().get_values()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        size_attributes = icp_sudo.get_param('size_attributes')
        stone_attributes = icp_sudo.get_param('stone_attributes')
        plating_attributes = icp_sudo.get_param('plating_attributes')

        res.update({
            'one_size_attribute': int(icp_sudo.get_param('one_size_attribute')),
            'one_size_value': int(icp_sudo.get_param('one_size_value')),
            'path_onpage_attachments': icp_sudo.get_param('path_onpage_attachments'),
            'onpage_token': icp_sudo.get_param('onpage_token'),
            'onpage_token_qty': icp_sudo.get_param('onpage_token_qty'),
            'single_stock': icp_sudo.get_param('single_stock')
        })
        if size_attributes:
            res.update(
                size_attributes=literal_eval(size_attributes),
            )
        if stone_attributes:
            res.update(
                stone_attributes=literal_eval(stone_attributes),
            )
        if plating_attributes:
            res.update(
                plating_attributes=literal_eval(plating_attributes),
            )

        return res

    def set_values(self):
        super().set_values()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        icp_sudo.set_param('one_size_attribute', self.one_size_attribute.id)
        icp_sudo.set_param('one_size_value', self.one_size_value.id)
        icp_sudo.set_param('size_attributes', self.size_attributes.ids)
        icp_sudo.set_param('stone_attributes', self.stone_attributes.ids)
        icp_sudo.set_param('plating_attributes', self.plating_attributes.ids)
        icp_sudo.set_param('path_onpage_attachments', self.path_onpage_attachments)
        icp_sudo.set_param('onpage_token', self.onpage_token)
        icp_sudo.set_param('onpage_token_qty', self.onpage_token_qty)
        icp_sudo.set_param('single_stock', self.single_stock)
