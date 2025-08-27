# -*- coding: utf-8 -*-
import binascii
from odoo import api, models, fields, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import json
import datetime

import logging
_logger = logging.getLogger(__name__)


class ODAS2MessageQueue(models.Model):
    _name = 'odas2.message.queue'
    _order = 'create_date desc, message_id desc'

    sender_id = fields.Char('Sender ID')
    receiver_id = fields.Char('Receiver ID')
    message_id = fields.Char('Message ID')
    access_token = fields.Char()
    op_code = fields.Char()
    data = fields.Text(dafault='')
    response_status = fields.Integer()
    response_message = fields.Text(default='')

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, rec.message_id))
        return res

    def action_process_message(self):
        for rec in self:
            try:
                # INFO: parses data as a json format.
                jdata = json.loads(rec.data)

                res_message, res_status = self.process_message_from_data(
                    rec.access_token,
                    rec.op_code,
                    rec.sender_id or 'MILOR',
                    rec.receiver_id or 'COMMERCEHUB',
                    jdata
                )
                rec.write({
                    'response_message': res_message,
                    'response_status': res_status
                })
            except Exception as e:
                msg = f"action_process_message {rec.message_id} exception: <{repr(e.args[0])}>."
                _logger.info(msg)

    @api.model
    def process_message_from_data(self, access_token, op_code, sender_id, receiver_id, data, host=''):
        # INFO: searches target company by access token.
        company = self.env['res.company'].sudo().search([('odas2_access_token', '=', access_token)], limit=1)
        # INFO: if wrong access_token then return forbidden.
        if not company:
            msg = f"No company found from access token."
            _logger.info(msg)
            return msg, 403

        is_a_testing_host = False
        if company.odas2_test_url_regex:
            import re
            is_a_testing_host = bool(re.search(company.odas2_test_url_regex, host))

        res_messages = []
        res_status = 200

        ProductProduct = self.env['product.product'].sudo()
        SaleOrder = self.env['sale.order'].sudo()
        SaleOrder.env.company = company
        ResPartner = self.env['res.partner'].sudo()
        IrAttachment = self.env['ir.attachment'].sudo()

        IrAttachment.env.company = company

        _logger.info(f"User: <{self.env.user.id}>.")

        _logger.info(f"Extracted company <{company.id}> from token <{access_token}>.")

        # INFO: checks if the op code asks to create a new SO.
        if op_code == 'CREATE_SALE_ORDER':

            for order in data:
                # INFO: builds sale_order 'origin' in two sides: poNumber / custOrderNumber
                #       poNumber is used to confirm PO / custOrderNumber is used to look for packing slips.
                order_po = order['poNumber']
                order_co = order['custOrderNumber']
                order_no = order_po + '/' + order_co
                order_as2_state = False
                order_as2_state_message = ''

                _logger.info(f"Looking for SO <{order_no}>.")
                # so_found = SaleOrder.search(['&', ('company_id', '=', company.id), ('origin', '=', order_no)], limit=1)
                so_found = SaleOrder.search([
                    ('company_id', '=', company.id),
                    ('commercehub_po', '=', order_po),
                    ('commercehub_co', '=', order_co)
                ], limit=1)
                if not so_found:
                    so_found = SaleOrder.search([
                        ('company_id', '=', company.id),
                        ('commercehub_co', '=', order_co)
                    ], limit=1)
                    if so_found:
                        order_as2_state = 'error'
                        order_as2_state_message = 'Duplicated SO.\n'

                    # INFO: catches stream checking company, sender (organization), receiver (partner) and the vendor.
                    vendor = order.get('vendor')
                    # INFO: defaults to 'qvc' because introduced later.
                    merchant = order.get('merchant', 'qvc')
                    as2_stream_id = self.env['odas2.stream'].search([
                        ('company_id', '=', company.id),
                        ('sender_id', '=', sender_id),
                        ('receiver_id', '=', receiver_id),
                        ('vendor_id', '=', vendor),
                        ('merchant_id', '=', merchant)
                    ], limit=1)
                    if not as2_stream_id:
                        msg = f"SO creation aborted: no stream found for AS2 PO <{order_no}>, sender <{sender_id}>, "\
                             f"receiver <{receiver_id}>, vendor <{vendor}>."
                        _logger.info(msg)
                        res_messages += [msg]
                        res_status = 400
                        break

                    # INFO: builds partner_shipping_id record (first try to search for it).
                    state = self.env['res.country.state'].search(
                        [('code', '=', order['shipTo']['state']),
                        ('country_id.code', '=', order['shipTo']['country'])],
                        limit=1
                    )
                    country = self.env['res.country'].search([('code', '=', order['shipTo']['country'])], limit=1)

                    pp = {
                        'name': (order['shipTo']['name1'] + ' ' + order['shipTo']['name2']).strip(),
                        'street': (order['shipTo']['address1'] + ' ' + order['shipTo']['address2']).strip(),
                        'city': order['shipTo']['city'],
                        'state_id': state and state.id,
                        'zip': order['shipTo']['postalCode'],
                        'country_id': country and country.id,
                        'phone': order['shipTo']['dayPhone'],
                        'email': order['shipTo']['email'],
                        'ref': ''
                    }

                    partner_shipping_id = ResPartner.search([
                        ('name', '=', pp['name']),
                        ('street', '=', pp['street']),
                        ('city', '=', pp['city']),
                        ('state_id', '=', state.id),
                        ('zip', '=', pp['zip']),
                        ('country_id', '=', country.id),
                        ('phone', '=', pp['phone']),
                        ('email', '=', pp['email']),
                    ], limit=1)

                    if not partner_shipping_id:
                        partner_shipping_id = ResPartner.create(pp)

                    lis = order.get('lineItems')

                    def check_pp(sku, field_name='commercehub_code'):
                        # _logger.info(f"Checking Vendor SKU <{sku}> by commercehub_complete_code")
                        # result = ProductProduct.search([('commercehub_complete_code', '=', sku)], limit=1)
                        # if not result:
                        _logger.info(f"Checking Vendor SKU <{sku}> by <{field_name}>")
                        result = ProductProduct.search([(field_name, '=', sku)], limit=1)
                        if result:
                            _logger.info(f"Found Vendor SKU <{sku}>")
                        return result

                    order_line, pps = [], []
                    for li in lis:
                        vendor_sku = li['vendorSKU']
                        _logger.info(f"Vendor SKU = <{vendor_sku}>")
                        pp = check_pp(vendor_sku)
                        if not pp:
                            # INFO: getting ready to inject code into commercehub_code when similar found.
                            _vendor_sku = False
                            _by = 'commercehub_code'
                            if len(vendor_sku) > 3:
                                # INFO: maybe XXXXXXXYYY and try to search XXXXXXX.YYY
                                _vendor_sku = vendor_sku[:-3] + '.' + vendor_sku[-3:]
                                pp = check_pp(_vendor_sku)
                                if not pp:
                                    # INFO: maybe XXXXXXXYYY and try to search XXXXXXX YYY
                                    _vendor_sku = vendor_sku[:-3] + ' ' + vendor_sku[-3:]
                                    pp = check_pp(_vendor_sku)
                            if not pp:
                                p_blank = vendor_sku.find(' ')
                                if p_blank > 0:
                                    _vendor_sku = vendor_sku[:p_blank] + '.' + vendor_sku[p_blank+1:]
                                    pp = check_pp(_vendor_sku)
                                    if not pp:
                                        # INFO: maybe XXXXXXX YYY and try to search XXXXXXXYYY
                                        _vendor_sku = vendor_sku.replace(' ', '')
                                        pp = check_pp(_vendor_sku)
                                else:
                                    # INFO: maybe XXXXXXX and try to search XXXXXXX.000 000
                                    _vendor_sku = vendor_sku + '.000 000'
                                    pp = check_pp(_vendor_sku)
                                    if not pp:
                                        # INFO: maybe XXXXXXX and try to search XXXXXXX.000 000 (default_code)
                                        pp = check_pp(_vendor_sku, 'default_code')
                                        _by = pp and 'default_code'
                                if not pp:
                                    p_min = vendor_sku.find('-')
                                    if p_min > 0:
                                        if not pp:
                                            # INFO: maybe XXXXXXX-YYYY and try to search XXXXXXX YYYY
                                            _vendor_sku = vendor_sku[:p_min] + ' ' + vendor_sku[p_min+1:]
                                            pp = check_pp(_vendor_sku)
                                        if not pp:
                                            # INFO: maybe XXXXXXX-YZZZ and try to search XXXXXXXY.ZZZ
                                            _vendor_sku = vendor_sku[:p_min+2] + '.' + vendor_sku[p_min+2:]
                                            pp = check_pp(_vendor_sku)
                                        if not pp:
                                            # INFO: maybe XXXXXXX-YYY and try to search XXXXXXX.YYY
                                            _vendor_sku = vendor_sku[:p_min] + '.' + vendor_sku[p_min+1:]
                                            pp = check_pp(_vendor_sku)
                                    # INFO: starts trying to locate product by altering default_code.
                                    _by = 'default_code'
                                    if not pp:
                                        # INFO: using straight default_code.
                                        _vendor_sku = vendor_sku
                                        pp = check_pp(_vendor_sku, _by)
                                    if not pp:
                                        # INFO: maybe XXXXXXXXXX YYY ZZZ and try to search XXXXXXXXXX.YYY ZZZ
                                        _vendor_sku = vendor_sku.split(' ')
                                        _vendor_sku = _vendor_sku[0] + '.' + ' '.join(_vendor_sku[1:])
                                        pp = check_pp(_vendor_sku, _by)
                            if pp:
                                # INFO: reset pp because actually we didn't find the original vendor_sku but we can
                                #       set what we have found instead.
                                msg = f"CommerceHub Vendor SKU: <{vendor_sku}> /  found by <{_by}> = <{_vendor_sku}>."
                                _logger.info(msg)
                                res_messages += [msg]
                                if company.odas2_pp_force_commercehub_code:
                                    pp.commercehub_code = vendor_sku
                                    msg = f"Product CommerceHub Code reset to: <{vendor_sku}>."
                                    _logger.info(msg)
                                    res_messages += [msg]

                        # INFO: if product does not exist and host url is a testing one then creates the product and sets
                        #       its template commercehub_code as the vendorSKU.
                        #       Only for testing purposes!!!
                        if not pp and is_a_testing_host:
                            pass

                        # INFO: creates an order line tuple and adds it to the order_line array (only if product exists).
                        if pp:
                            # INFO: message from packing slip can contain useless text instead personalized name,
                            #       extract only name ('terminated by '##') or get all (if there is no '##').
                            ps_msg = li.get('packslipMessage', '')
                            ps_msg = (ps_msg.find('##') >= 0) and ps_msg.split('##') or ['']
                            vals = {
                                'name': li['description'],
                                'product_id': pp.id,
                                'product_uom_qty': li['qtyOrdered'],
                                'price_unit': li['unitPrice'],
                                'custom_value': ps_msg[0],
                                'commercehub_sale_order_id': False,
                                'commercehub_po': order_po,
                                'commercehub_co': order_co,
                                'as2_metadata': li['merchantLineNumber'] + '\n' +
                                    li['shippingCode'] + '\n' +
                                    li['shippingLabel/trackingNumber']
                            }

                            # INFO: mandatory ',' at the end of the below sentence (otherwise not creating tuples).
                            order_line += (0, 0, vals),

                            # INFO: checks on missing custom_value only for PERSONALIZED = TEXT products.
                            if not vals['custom_value']:
                                personalized = pp.with_context(lang=None).product_template_attribute_value_ids. \
                                           filtered(lambda self: self.attribute_id.name == 'PERSONALIZED').name
                                if personalized == 'TEXT':
                                    order_as2_state = 'error'
                                    order_as2_state_message += 'Missing custom_value for product <%s>.\n' % (pp.default_code or '')

                        else:
                            msg = f"SO creation aborted: AS2 PO <{order_no}> has got a product <{vendor_sku}> that does not exist."
                            _logger.info(msg)
                            res_messages += [msg]
                            res_status = 400
                            order_line = []
                            break
                    try:
                        if order_line:
                            _logger.info(f"Extracted company <{SaleOrder.env.company.id}> from AS2 PO <{order_no}> (pre create).")

                            vals = {
                                'company_id': company.id,
                                'origin': order_no,
                                'from_as2': True,
                                'last_update_from_as2': datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                # 'partner_invoice_id': self.partner_address_13.id,
                                'partner_shipping_id': partner_shipping_id.id,
                                'order_line': order_line,
                                # INFO: sets as seen in OdAS2 setting page.
                                'partner_id': company.odas2_so_partner_id.id,
                                'source_id': as2_stream_id.source_id.id,
                                'commercehub_sale_order_id': False,  # INFO: remember to use order_id instead.
                                'commercehub_po': order_po,
                                'commercehub_co': order_co,
                                'user_id': company.odas2_so_user_id.id,
                                # 'state': 'done',
                                'as2_state': order_as2_state,
                                'as2_state_reason': order_as2_state_message,
                                'as2_stream_id': as2_stream_id.id
                            }
                            if company.odas2_so_pricelist_id:
                                vals['pricelist_id'] = company.odas2_so_pricelist_id.id,
                            so = SaleOrder.create(vals)
                            _logger.info(f"Extracted company <{SaleOrder.env.company.id}> from SO <{so.name}> (post create).")
                            msg = f"AS2 PO <{order_no}> -> created Odoo SO <{so.name}>."
                            _logger.info(msg)
                            res_messages += [msg]

                            # INFO: loops thru products inside SO lines and updates stream product_ids if necessary.
                            if as2_stream_id.auto_add_product:
                                product_ids = []
                                for ol in so.order_line:
                                    if ol.product_id:
                                        product_ids += [(4, ol.product_id.id, 0)]
                                as2_stream_id.product_ids = product_ids

                                # else:
                        #     msg = f"Empty AS2 PO <'{order_no}'>."
                        #     _logger.info(msg)
                        #     res_messages += [msg]
                        #     res_status = 299

                    except Exception as e:
                        msg = f"process_message_from_data when creating SO {order_no} exception: <{repr(e.args[0])}>."
                        _logger.info(msg)
                        res_messages += [msg]
                        res_status = 500
                else:
                    msg = f"AS2 PO <{order_no}> -> already created SO <{so_found.name}>."
                    _logger.warning(msg)
                    res_messages += [msg]
                    res_status = (res_status < 300) and 299 or res_status
        # INFO: checks if the op code asks to attach packing slip to a previous created SO.
        elif op_code == 'ATTACH_PACKING_SLIP':
            for ps in data:
                order_no = ps.get('order_no')
                pdf = ps.get('pdf')
                if not order_no:
                    msg = f"Empty order_no from OdAS2 Gateway."
                    _logger.info(msg)
                    res_messages += [msg]
                    res_status = (res_status < 300) and 299 or res_status
                elif not pdf:
                    msg = f"Empty PDF order_no <{order_no} from OdAS2 Gateway."
                    _logger.info(msg)
                    res_messages += [msg]
                    res_status = (res_status < 300) and 299 or res_status
                else:
                    pdf_name = ps.get('name')
                    att = IrAttachment.search([('name', '=', pdf_name)], limit=1)
                    if att:
                        msg = f"Same name attachment <{pdf_name}> already found."
                        _logger.info(msg)
                        res_messages += [msg]
                        res_status = (res_status < 300) and 299 or res_status
                    else:
                        # INFO: searches SO thru commercehub_co and using right company.
                        so = SaleOrder.search([
                            ('commercehub_co', '=', order_no),
                            ('company_id', '=', company.id)], limit=1)
                        try:
                            out_file = binascii.a2b_base64(pdf)
                            # INFO: we need to change user (sudoing) owner of message record because of prevent policy
                            #       that blocks public and portal users from using attachments that are not theirs.
                            #       Remember that here you are portal user because in a route.
                            #       Checks /doo13/odoo/addons/mail/models/mail_thread.py function
                            #       _message_post_process_attachments(...)
                            if so:
                                so.with_user(SUPERUSER_ID).message_post(body='Packing Slip from OdAS2',
                                                                        attachments=[(pdf_name, out_file)])
                                msg = f"Attached packing slip <{pdf_name}> to <{so.name}/{order_no}>."
                                _logger.info(msg)
                                res_messages += [msg]
                            else:
                                msg = f"Missing SO number <{order_no}>."
                                _logger.info(msg)
                                res_messages += [msg]
                                res_status = 400
                                if company.odas2_ps_mail_channel_id_when_orphan:
                                    # INFO: sends orphans packing slip to channel set in OdAS2 config.
                                    company.odas2_ps_mail_channel_id_when_orphan.with_user(SUPERUSER_ID).\
                                        with_context(mail_create_nosubscribe=True).message_post(
                                        body=f"Missing SO number <{order_no}>: orphan packing slip",
                                        message_type='comment',
                                        subtype='mail.mt_comment',
                                        attachments=[(pdf_name, out_file)]
                                    )
                        except Exception as e:
                            msg = f"process_message_from_data when message_post exception: <{repr(e.args[0])}>."
                            _logger.info(msg)
                            res_messages += [msg]
                            res_status = 500

        return '\n'.join(res_messages), res_status
