from odoo import fields, models, api

class ProposalSaleOrderLine(models.Model):
    _inherit = 'proposal.sale.order.line'

    #product_values_ids = fields.Many2many('product.template.attribute.value', string='Varianti/opzioni',
                                          #compute='_compute_prod_atts_vals')

    product_attributes = fields.Text(string='Varianti/opzioni',
                                          compute='_compute_prod_atts_text')

    na_product_id = fields.Many2one(
        'product.template', string='Product',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)


    #@api.depends('na_product_id')
    #def _compute_prod_atts_vals(self):
        #for rec in self:
            #if rec.na_product_id.attribute_line_ids:
                #ids_list = []
                #attribute_lines_ids = rec.na_product_id.attribute_line_ids
                #for line in attribute_lines_ids:
                    #ids_list += line.product_template_value_ids.mapped('id')
                #rec.product_values_ids = self.env['product.template.attribute.value'].search([('id', 'in', ids_list)])
            #else:
                #rec.product_values_ids = None

    @api.depends('na_product_id')
    def _compute_prod_atts_text(self):
        for rec in self:
            if rec.na_product_id.attribute_line_ids:
                att_values_dict = {}
                attribute_lines_ids = rec.na_product_id.attribute_line_ids
                for line in attribute_lines_ids:
                    att_name = str(line.attribute_id.name)
                    value_num = 1
                    values_list = ''
                    len_values = len(line.value_ids)
                    for value in line.value_ids:
                        if len_values == 1 or value_num == len_values:
                            values_list += str(value.name)
                        else:
                            values_list += (str(value.name) + ' / ')
                        value_num += 1
                    att_values_dict[att_name] = values_list
                product_attributes_str = ''
                for key, value in att_values_dict.items():
                    product_attributes_str += key + ' :  ' + value + '\n'
                rec.product_attributes = product_attributes_str
            else:
                rec.product_attributes = None

    @api.onchange('na_product_id')
    def _onchange_product_id(self):
        if self.na_product_id:
            self.product_id = self.na_product_id.product_variant_ids[0].id

class ProposalSaleOrder(models.Model):
    _inherit = "proposal.sale.order"

    type = fields.Selection(selection_add=[('na_mto', 'From order template')])

