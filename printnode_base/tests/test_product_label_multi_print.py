# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from random import randint

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestPrintNodeCommon


@tagged('post_install', '-at_install', 'pn_product_label_multi_print')  # can be run by test-tag
class TestPrintNodeProductLabelMultiPrint(TestPrintNodeCommon):
    """Tests of ProductLabelMultiPrint wizard methods"""

    def setUp(self):
        super(TestPrintNodeProductLabelMultiPrint, self).setUp()

        self.wizard = self.env['product.label.multi.print'].create({
            'report_id': self.report.id,
        })

    def test_get_report(self):
        """
        Test for correct getting report
        """

        self.assertEqual(self.wizard.get_report(), self.report)

    def test_change_wizard_printer(self):
        """
        Change printer Test when report_id changes
        """

        test_printer = self.env['printnode.printer'].create({
            'name': 'Test Printer',
            'status': 'offline',
            'computer_id': self.computer.id,
        })
        self.wizard.printer_id = test_printer

        self.env.company.printnode_printer = self.printer
        self.assertEqual(self.wizard.printer_id, test_printer)

        self.wizard._change_wizard_printer()
        self.assertEqual(self.wizard.printer_id, self.printer)

    def test_open_product_product_multi_printing_wizard(self):
        """
        Test creating product_multi_printing_wizard
        """

        self.env.user.printnode_printer = self.printer

        prod_prod = self.env['product.product'].create({
            'name': 'product_variant_1',
        })
        wizard = self._up_multiprint_wizard(prod_prod)

        self.assertEqual(self.env.user.printnode_printer.id, wizard.printer_id.id)

        self.assertEqual(len(wizard.product_line_ids), 1)

        product_line = wizard.product_line_ids
        self.assertEqual(product_line.product_id.id, prod_prod.id)

        self.assertEqual(product_line.quantity, 1)

        with self.assertRaises(ValidationError):
            product_line.write({'quantity': 0})

    def test_open_product_template_multi_printing_wizard(self):
        """
        Test creating product_template_multi_printing_wizard
        """

        self.env.user.printnode_printer = self.printer

        prod_tmpl = self.env['product.template'].create({
            'name': 'product_template_1',
        })
        wizard = self._up_multiprint_wizard(prod_tmpl)

        self.assertEqual(self.env.user.printnode_printer.id, wizard.printer_id.id)

        self.assertEqual(len(wizard.product_line_ids), 1)

        product_line = wizard.product_line_ids
        related_prod_prod = prod_tmpl.product_variant_ids
        self.assertEqual(product_line.product_id.id, related_prod_prod.id)

        self.assertEqual(product_line.quantity, 1)

        with self.assertRaises(ValidationError):
            product_line.write({'quantity': 0})

    def test_open_stock_picking_multi_printing_wizard(self):
        """
        Test creating stock_picking_multi_printing_wizard
        """

        products = []
        total_qty = 0
        self.env.user.printnode_printer = self.printer

        for i in range(1, 6):
            product = self.env['product.product'].create({
                'name': 'product_{}'.format(i),
                'type': 'product',
            })
            qty = randint(1, 5)
            total_qty += qty
            products.append((product, qty))

        self.customer = self.env['res.partner'].create({
            'name': 'Customer',
        })
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line':
                [(0, 0, {'product_id': prod.id, 'product_uom_qty': qty}) for prod, qty in products],
        })
        self.sale_order.action_confirm()

        wh_out = self.sale_order.picking_ids[:1]
        wizard = self._up_multiprint_wizard(wh_out)

        self.assertEqual(self.env.user.printnode_printer.id, wizard.printer_id.id)

        self.assertEqual(len(wizard.product_line_ids), len(products))

        self.assertEqual(len(wizard.get_docids()), total_qty)

        product_lines = wizard.product_line_ids

        for line in product_lines:
            with self.assertRaises(ValidationError):
                line.write({'quantity': 0})
