# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from odoo import exceptions, fields, models, api, _

from ..models.res_company import REPORT_DOMAIN


class ProductLabelMultiPrint(models.TransientModel):
    _name = 'product.label.multi.print'
    _inherit = 'printnode.report.abstract.wizard'
    _description = 'Print Product Labels'

    report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        domain=REPORT_DOMAIN,
        default=lambda self: self._default_report(),
    )
    product_line_ids = fields.One2many(
        comodel_name='product.label.multi.print.line',
        inverse_name='wizard_id',
        string='Products',
    )

    def _default_report(self):
        return self.env.company.def_wizard_report_id

    def _get_available_reports(self):
        return self.env.company.wizard_report_ids

    def _default_printer_id(self):
        """
        Return default printer for wizard
        """
        # There can be default report from settings (this method called before the deafult value
        # to report_id will be applied)
        report_id = self.report_id or self.env.company.def_wizard_report_id

        # User rules
        user_rules_printer_id = self.env['printnode.rule'].search([
            ('user_id', '=', self.env.uid),
            ('report_id', '=', report_id.id),  # There will be no rules for report_id = False
        ], limit=1).printer_id

        # Workstation printer
        workstation_printer_id = self.env.user._get_workstation_device(
            'printnode_workstation_printer_id')

        # Priority:
        # 1. Printer from User Rules (if exists)
        # 2. Default Workstation Printer (User preferences)
        # 3. Default printer for current user (User Preferences)
        # 4. Default printer for current company (Settings)
        return user_rules_printer_id or workstation_printer_id or \
            self.env.user.printnode_printer or self.env.company.printnode_printer

    @api.onchange('report_id')
    def _change_wizard_printer(self):
        self.printer_id = self._default_printer_id()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(ProductLabelMultiPrint, self).fields_get()

        available_report_ids = self._get_available_reports()
        if available_report_ids:
            res['report_id']['domain'] = [('id', 'in', available_report_ids.ids)]
        return res

    def get_action(self):
        self.ensure_one()
        view = self.env.ref('printnode_base.product_label_multi_print_form')
        action = {
            'name': _('Print Product Labels'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.multi.print',
            'views': [(view.id, 'form')],
            'target': 'new',
            'res_id': self.id,
        }
        return action

    def get_report(self):
        self.ensure_one()
        return self.report_id

    def get_docids(self):
        self.ensure_one()
        objects = self.env['product.product']

        for line in self.product_line_ids:
            # pylint:disable=W0612
            for i in range(line.quantity):
                objects = objects.concat(line.product_id)
        return objects


class ProductLabelMultiPrintLine(models.TransientModel):
    _name = 'product.label.multi.print.line'
    _description = 'Print Product Labels / Line'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
    )

    quantity = fields.Integer(
        required=True,
        default=1,
    )

    wizard_id = fields.Many2one(
        comodel_name='product.label.multi.print',
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity < 1:
                raise exceptions.ValidationError(
                    _(
                        'Quantity can not be less than 1 for product {product}'
                    ).format(**{
                        'product': rec.product_id.display_name,
                    })
                )
