# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import os
from pathlib import Path
import logging
import base64

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def send_email(self, email_to, file_name):
        try:
            # retrieving the template used for the email
            template_id = self.env.ref('na_bijou.mail_template_send_bl')
            create_values = template_id.generate_email(self.id)  # res_id

            # setting the sender email
            if not create_values['email_from']:
                create_values['email_from'] = template_id.mail_server_id.smtp_user

            # setting the reciever email
            create_values['email_to'] = email_to

            mail = self.env['mail.mail'].create(create_values)
            mail.attachment_ids = file_name
            mail.sudo().send()
        except Exception as e:
            _logger.error("Error in sending the email with the .bl file attached: " + str(e))

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        if self.origin_sale_id.source_id.name != 'BIJOU':
            return res
        # setting the name of the file
        file_name = 'bijou.bl'
        file_dir_name = str(Path.home()) + '/' + file_name

        # setting the various data needed to compile the head of the .bl
        no_bdl = self.id
        no_cde = self.origin
        total_price = 0
        num_of_lines = 0
        validation_date = self.write_date.date()
        for move_id in self.move_ids_without_package:
            total_price += move_id.sale_price
            num_of_lines += 1

        # creating the head of the .bl
        bl_head = """[ENTETE]
TYPE = LIVRAISON
CL LIV = """ + str(self.origin_sale_id.partner_id.fm_code) + """
CL CDE = """ + str(self.origin_sale_id.partner_id.fm_code) + """
NO BDL = """ + str(no_bdl) + """
DAT BDL = """ + str(validation_date.day).zfill(2) + str(validation_date.month).zfill(2) + str(validation_date.year) + """
EMAIL = edi@milor.it
NO CDE = """ + no_cde + """
COUR M1 =
DEVISE = EUR
QTE TOT = """ + str(self.quantity_total) + """
PA TOT = """ + str(total_price) + """
NBLIG = """ + str(num_of_lines)

        # creating the bijou.bl file
        with open(file_dir_name, 'w') as bl:

            # add the head to the file
            bl.write(bl_head + '\n')

            # retrieve all the order lines inside the transfer
            for move_id in self.move_ids_without_package:

                # assigning the ref_customer_code becauase it's not assigned in the attachment_to_order func
                # because the BOX elements are not retrieved from the .cde but created afterwards
                if "BOX" in move_id.product_id.default_code:
                    move_id.origin_sale_line_id.ref_customer_code = move_id.origin_sale_line_id.product_id.default_code

                # set the product name
                prod_name = str(move_id.product_id.name)
                if move_id.product_id.stone_name:
                    prod_name += ' (' + str(
                        move_id.origin_sale_line_id.product_id.stone_name) + ')'

                # check if the variables used to create the lines in the file are ok
                sale_price = ""
                customer_code = ""
                qty_done = ""

                if prod_name == 'False':
                    prod_name = ""

                if move_id.sale_price:
                    sale_price = str(move_id.sale_price)

                if move_id.origin_sale_line_id.ref_customer_code:
                    customer_code = str(move_id.origin_sale_line_id.ref_customer_code)

                if move_id.quantity_done:
                    qty_done = str(move_id.quantity_done)

                # create the line for each product
                bl_line = """[LIGNE]
REF FOU = """ + move_id.product_id.default_code + """
QTE = """ + qty_done + """
PA NET = """ + sale_price + """
REF CLI = """ + customer_code + """
TVA =
LIBELLE = """ + prod_name + """
TITRE M1 =
NAT M1 =
PDS M1 =
COUR M1 =
COD PIE1 =
PDS PIE1 = """ + '\n'
                bl.write(bl_line)
            bl.write('[FIN]')
            bl.close()
        with open(file_dir_name, 'rb') as bl:
            # create the attachment

            data = bl.read().replace(b'\n', b'\r\n')

            bl_file = self.env['ir.attachment'].create({
                'datas': base64.b64encode(data),
                'name': str(self.origin_sale_id.partner_id.fm_code) + '.bl',
                'mimetype': 'application/txt',
            })
            bl.close()
        self.send_email(self.origin_sale_id.bl_email, bl_file)

        # delete the file from the computer (can be found as an attachment in the email)
        os.remove(file_dir_name)

        return res
