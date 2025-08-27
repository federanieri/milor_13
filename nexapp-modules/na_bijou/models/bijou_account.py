# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import logging
from datetime import datetime

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BijouAccount(models.Model):
    _name = "bijou.account"

    name = fields.Char(string="Account Name")
    mail = fields.Char(string="Mail")

    last_synch = fields.Datetime(string="Last Synch Date")

    logging_ids = fields.One2many(
        comodel_name='ir.logging',
        inverse_name='bijou_id',
        string='Loggins', ondelete='set null')

    def find_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id('sale',
                                                              'action_quotations_with_onboarding')
        action['domain'] = [('client_mail', '=', self.mail)]
        action['context'] = {}
        return action

    def _log_message(self, message, func='', line='0'):
        with self.pool.cursor() as cr:
            cr.execute("""
                INSERT INTO
                    ir_logging(create_date, name, type, message, bijou_id, path, func, line)
                VALUES
                (NOW() at time zone 'UTC', '{}', '{}', '{}', {}, '{}', '{}', '{}')
            """.format(message, 'import', message, str(self.id), '/', func, line))

    def synch_bijou(self):
        if self:
            attachments = self.find_attachments()
        else:
            attachments = self.find_bijou_account()

        if attachments[0] and attachments[1]:
            self.attachment_to_order(attachments[1])
            for account in attachments[0]:
                account.last_synch = datetime.now()
        pass

    def find_bijou_account(self):
        bijou_account_ids = self.env['bijou.account'].search([])
        return bijou_account_ids.find_attachments()

    def find_attachments(self):
        list_attachments = []
        for account in self:
            edi_project = self.env['project.project'].search([('alias_name', '=', 'edi')])
            if edi_project:
                edi_tasks = self.env['project.task'].search(
                    [('project_id', '=', edi_project.id), ('create_date', '>', account.last_synch),
                     ('attachment_ids', '!=', False)])
                for task in edi_tasks:
                    for message in task.message_ids:
                        for attachment in message.attachment_ids:
                            list_attachments.append([account, attachment])
                if list_attachments:
                    return [self, list_attachments]
        return [[], False]

    @api.model
    def get_domain_contact(self, name):
        domain = []
        domain.append(('name', '=', name))
        return domain

    def attachment_to_order(self, attachments=[]):
        msg_log = ''
        error_msg = 'Errore durante importazione del file .cde. Per favore verificare i dati nel file. '

        try:
            # setting the keys of the dictionary for the head of the .cde
            dict_key_client_code = 'CL CDE'
            dict_key_order_code = 'NO CDE'
            dict_key_customer_email = 'EMAIL'
            dict_key_order_date = 'DAT CDE'
            dict_key_notes = 'COMM'

            # setting the value of the keys of the dictionary for the sale order lines of the .cde
            dict_key_id = 'REF FOU'
            dict_key_qty = 'QTE'
            dict_key_price = 'PA HT'
            dict_key_product_ref_customer = 'REF CLI'
            dict_key_size = "TAILLE"

            for document in attachments:
                for attachment in document[1]:
                    msg_log = ''
                    if '.cde' in attachment.name.lower():
                        file_data = str(base64.b64decode(attachment.datas))
                        file_data = file_data.replace('\"', '')

                        # orders_list = list with all the orders
                        orders_list = file_data.split("[ENTETE]")

                        # removing the first element because is just a formatting element
                        orders_list.pop(0)

                        # looping through each order
                        for order in orders_list:
                            if dict_key_client_code not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_client_code + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_order_code not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_order_code + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_customer_email not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_customer_email + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_order_date not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_order_date + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_id not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_id + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_qty not in order:
                                msg_log = "Allegato non elaborato. Chiave " + dict_key_qty + " non trovata. " + attachment.name
                                attachments[0][0]._log_message(msg_log)
                                break
                            elif dict_key_notes not in order:
                                order_notes = ''

                            prods_data_dict = {}

                            # prods_list = list with all the lines of a single order
                            prods_list = order.split("[LIGNE]")

                            # prod = list with all the values and fields of a sale order line
                            for prod in prods_list:
                                prod_data_list_dict = {}
                                prod = prod.split('\\r\\n')
                                # remove the first and the last element because are just empty quotes
                                prod.pop(0)
                                prod.pop()

                                # check if there is a head
                                if dict_key_order_code in str(prod):

                                    # head_data = single value and field of head of the sale order
                                    # (there can be more than one sale order in one .cde)

                                    for head_data in prod:
                                        head_field_value = head_data.split(' = ')
                                        if head_field_value[0] == dict_key_customer_email:
                                            bl_mail = head_field_value[1]
                                        elif head_field_value[0] == dict_key_order_date:
                                            day = head_field_value[1][:2]
                                            month = head_field_value[1][2:4]
                                            year = head_field_value[1][4:8]
                                            order_date = day + '/' + month + '/' + year + ' 08:00:00'
                                            order_date = datetime.strptime(order_date,
                                                                           '%d/%m/%Y %H:%M:%S')
                                            print(order_date)
                                        elif head_field_value[0] == dict_key_client_code:
                                            client_code = head_field_value[1]
                                            res_partner = self.env['res.partner']
                                            if client_code:
                                                last = client_code[-1]
                                                if len(client_code) == 9 and last.isalpha():
                                                    client_code = str(int(client_code[0:-1]))
                                                    client_code_string = '%s%s' % (
                                                        'CL', client_code)
                                                elif client_code.isnumeric():
                                                    client_code = str(int(client_code))
                                                    client_code_string = '%s%s' % (
                                                        'CL', client_code)
                                                else:
                                                    client_code_string = client_code
                                                partner_id = res_partner.search(
                                                    [('fm_code', '=', client_code_string)],
                                                    limit=1).id
                                                # if not res_partner:
                                                #     domain = self.get_domain_contact(bl_mail)
                                                #     res_partner = res_partner.search(domain, limit=1)
                                        elif head_field_value[0] == dict_key_notes:
                                            order_notes = head_field_value[1]
                                    # delete the head of the .cde because it cannot be processed
                                    prod.pop(0)
                                    continue

                                # prod_data = single value and field pair of sale order line
                                for prod_data in prod:

                                    # prod_data_list_dict = dictionary with all the data and fields separated (later needed to create a dictionary)
                                    field_value = prod_data.split(' = ')
                                    if len(field_value) > 1:
                                        prod_data_list_dict.update({field_value[0]: field_value[1]})

                                # prod_data_dict = dictionary having the key as the prod. code and as value a dictionary made of all the data of a sale order line
                                try:
                                    prod_data_list_dict[dict_key_id]
                                except Exception as e:
                                    continue
                                prod_data_dict = {
                                    prod_data_list_dict[dict_key_id]: prod_data_list_dict}
                                prods_data_dict.update(prod_data_dict)

                            if not partner_id:
                                attachments[0][0]._log_message(
                                    'Cliente non trovato' + '. {}'.format(attachment.name),
                                    '')
                                break

                            source_id = self.env['utm.source'].search([('name', '=', 'BIJOU')]).id

                            try:
                                bijou_sale_order = self.env['sale.order'].create({
                                    'partner_id': partner_id,
                                    'create_date': order_date,
                                    'origin': attachment[0].id,
                                    'source_id': source_id,
                                    'client_mail': attachments[0][0].mail,
                                    'bl_email': bl_mail,
                                    'note': order_notes,
                                })
                                partner_id = self.env['res.partner']
                                bl_mail = ''
                                order_date = None
                            except Exception:
                                msg_log = error_msg
                                attachments[0][0]._log_message(
                                    msg_log + '. {}'.format(attachment.name),
                                    '')
                                break

                            for prod in prods_data_dict:
                                product = self.env['product.product'].search(
                                    [('default_code', '=', prod)])
                                prod_id = self.env['product.product'].search(
                                    [('default_code', '=', prod)]).id

                                if not prod_id:

                                    # if the product has not been found probably has a size specified
                                    # in the following lines the size of the product is searched and later on associated
                                    # with an existing product
                                    if dict_key_size in prods_data_dict[prod]:
                                        product_size_fr = prods_data_dict[prod][dict_key_size]
                                        product_size_it = self.env['ring.size.conversion'].search(
                                            [('french_size', '=', product_size_fr)]).italian_size

                                        product_variants = self.env['product.product'].search(
                                            [('default_code', 'like', prod)])

                                        # finding the correct product that matches the size
                                        for product_variant in product_variants:
                                            if \
                                                    product_variant.product_template_attribute_value_ids.read()[
                                                        0][
                                                        'attribute_line_id'][
                                                        1] == 'TAGLIA' or 'SIZE':
                                                if float(
                                                        product_variant.product_template_attribute_value_ids.read()[
                                                            0][
                                                            'name']) == product_size_it:
                                                    prod_id = self.env['product.product'].search(
                                                        [('default_code', '=',
                                                          product_variant.default_code)]).id
                                                    product = self.env['product.product'].search(
                                                        [('default_code', '=',
                                                          product_variant.default_code)])
                                    else:
                                        msg_log += " Prodotto non trovato " + prod
                                        continue

                                prod_price = self.env['product.product'].search(
                                    [('id', '=', prod_id)]).lst_price
                                if dict_key_price in prods_data_dict[prod]:
                                    prod_price = float(prods_data_dict[prod][dict_key_price])

                                try:
                                    if dict_key_qty in prods_data_dict[prod]:
                                        prod_qty = float(prods_data_dict[prod][dict_key_qty])
                                    else:
                                        msg_log += " Quantità non trovata per prodotto " + prod
                                        continue
                                except Exception as e:
                                    continue

                                product_ref_customer = ''
                                if dict_key_product_ref_customer in prods_data_dict[prod]:
                                    product_ref_customer = prods_data_dict[prod][
                                        dict_key_product_ref_customer]

                                self.env['sale.order.line'].create({
                                    'name': "[" + product.default_code + "] " + product.name,
                                    'order_id': bijou_sale_order.id,
                                    'product_id': prod_id,
                                    'product_uom_qty': prod_qty,
                                    'retail_price': prod_price,
                                    'ref_customer_code': product_ref_customer
                                })
                            try:
                                if bijou_sale_order.order_line:
                                    if msg_log == '':
                                        attachments[0][0]._log_message(
                                            'Elaborato allegato {}'.format(attachment.name),
                                            '')
                                    else:
                                        attachments[0][0]._log_message(
                                            msg_log + ' Elaborato allegato {}'.format(
                                                attachment.name),
                                            '')
                                else:
                                    attachments[0][0]._log_message(
                                        'Allegato non elaborato. Controllarne i dati. {}'.format(
                                            attachment.name),
                                        '')
                                    bijou_sale_order.unlink()
                            except:
                                attachments[0][0]._log_message(
                                    'Allegato non elaborato. Controllarne i dati. {}'.format(
                                        attachment.name),
                                    '')
            # check sync della data
        except Exception as e:
            msg_log = error_msg
            error = error_msg
            if type(e) == KeyError:
                msg_error = str(e.args[0])
                error = "Chiave {} mancante".format(msg_error)
            attachments[0][0]._log_message(error + '. {}'.format(attachment.name),
                                           '')
            if not attachments:
                msg_log = 'Nessun allegato trovato.'
            raise UserError(msg_log)
        return
