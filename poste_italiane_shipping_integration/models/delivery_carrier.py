import logging
import requests
import json
from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[("poste_italiane_provider", "Poste Italiane")])
    poste_italiane_provider_package_id = fields.Many2one('product.packaging', string="Package Info",
                                                         help="Default Package")
    poste_italiane_cost_center_code = fields.Char(string="Cost Center Code", copy=False)

    poste_italiane_product = fields.Selection([('APT000902', 'Poste Delivery Business Standard'),
                                               ('APT000901', 'Poste Delivery Business Express'),
                                               ('APT000904', 'PosteDelivery Business International Standard'),
                                               ('APT000903', 'PosteDelivery Business International Express'),
                                               ], string="Print Format", default='APT000901')

    poste_italiane_print_format = fields.Selection([('A4', 'A4'),
                                                    ('ZPL', 'ZPL'),
                                                    ('1011', '1011'),
                                                    ], string="Product", default='A4')

    def check_address_details(self, address_id, required_fields):
        """
            check the address of Shipper and Recipient
            param : address_id: res.partner, required_fields: ['zip', 'city', 'country_id', 'street']
            return: missing address message
        """

        res = [field for field in required_fields if not address_id[field]]
        if res:
            return "Missing Values For Address :\n %s" % ", ".join(res).replace("_id", "")

    def poste_italiane_provider_rate_shipment(self, order):
        return {'success': True, 'price': 0.0, 'error_message': False, 'warning_message': False}

    def poste_italiane_provider_retrive_single_package_info(self, height=False, width=False, length=False, weight=False,
                                                            package_name=False):
        return {
            "weight": weight,
            "height": height,
            "length": length,
            "width": width
        }

    def poste_italiane_provider_packages(self, picking):
        package_list = []
        weight_bulk = picking.weight_bulk
        package_ids = picking.package_ids
        for package_id in package_ids:
            height = package_id.packaging_id and package_id.packaging_id.height or 0
            width = package_id.packaging_id and package_id.packaging_id.width or 0
            length = package_id.packaging_id and package_id.packaging_id.length or 0
            weight = package_id.shipping_weight
            package_name = package_id.name
            package_list.append(
                self.poste_italiane_provider_retrive_single_package_info(height, width, length, weight, package_name))
        if weight_bulk:
            height = self.poste_italiane_provider_package_id and self.poste_italiane_provider_package_id.height or 0
            width = self.poste_italiane_provider_package_id and self.poste_italiane_provider_package_id.width or 0
            length = self.poste_italiane_provider_package_id and self.poste_italiane_provider_package_id.length or 0
            weight = weight_bulk
            package_name = picking.name
            package_list.append(
                self.poste_italiane_provider_retrive_single_package_info(height, width, length, weight, package_name))
        return package_list

    def poste_italiane_provider_create_shipment(self, request_type, api_url, request_data, header):
        _logger.info("Shipment Request API URL:::: %s" % api_url)
        _logger.info("Shipment Request Data:::: %s" % request_data)
        response_data = requests.request(method=request_type, url=api_url, headers=header, data=request_data)
        if response_data.status_code in [200, 201]:
            response_data = response_data.json()
            _logger.info(">>> Response Data {}".format(response_data))
            return True, response_data
        else:
            return False, response_data.text

    def poste_italiane_provider_send_shipping(self, picking):
        shipper_address_id = picking.picking_type_id and picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.partner_id
        recipient_address_id = picking.partner_id
        company_id = self.company_id
        shipper_address_error = self.check_address_details(shipper_address_id, ['zip', 'city', 'country_id', 'street'])
        recipient_address_error = self.check_address_details(recipient_address_id,
                                                             ['zip', 'city', 'country_id', 'street'])
        if shipper_address_error or recipient_address_error or not picking.shipping_weight:
            raise ValidationError("%s %s  %s " % (
                "Shipper Address : %s \n" % (shipper_address_error) if shipper_address_error else "",
                "Recipient Address : %s \n" % (recipient_address_error) if recipient_address_error else "",
                "Shipping weight is missing!" if not picking.shipping_weight else ""
            ))

        sender_zip = shipper_address_id.zip or ""
        sender_city = shipper_address_id.city or ""
        sender_country_code = shipper_address_id.country_id and shipper_address_id.country_id.code or ""
        sender_state_code = shipper_address_id.state_id and shipper_address_id.state_id.code or ""
        sender_street = shipper_address_id.street or ""
        sender_phone = shipper_address_id.phone or ""
        sender_email = shipper_address_id.email or ""

        receiver_zip = recipient_address_id.zip or ""
        receiver_city = recipient_address_id.city or ""
        receiver_country_code = recipient_address_id.country_id and recipient_address_id.country_id.code or ""
        receiver_state_code = recipient_address_id.state_id and recipient_address_id.state_id.code or ""
        receiver_street = recipient_address_id.street or ""
        receiver_phone = recipient_address_id.phone or ""
        receiver_email = recipient_address_id.email or ""

        packages = self.poste_italiane_provider_packages(picking)
        try:
            request_data = json.dumps({
                "costCenterCode": self.poste_italiane_cost_center_code,
                "paperless": "false",
                "shipmentDate": picking.scheduled_date.strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "waybills": [
                    {
                        "printFormat": self.poste_italiane_print_format,
                        "product": self.poste_italiane_product,
                        "data": {
                            "declared": packages,
                            "services": {},
                            "sender": {
                                "zipCode": sender_zip,
                                "city": sender_city,
                                "address": sender_street,
                                "country": shipper_address_id.country_id and shipper_address_id.country_id.country_iso_code,
                                "countryName": shipper_address_id.country_id and shipper_address_id.country_id.name,
                                "nameSurname": shipper_address_id.name,
                                "province": sender_state_code,
                                "email": sender_email,
                                "phone": sender_phone,
                            },
                            "receiver": {
                                "zipCode": receiver_zip,
                                "city": receiver_city,
                                "address": receiver_street,
                                "country": recipient_address_id.country_id and recipient_address_id.country_id.country_iso_code,
                                "countryName": recipient_address_id.country_id and recipient_address_id.country_id.name,
                                "nameSurname": recipient_address_id.name,
                                "province": receiver_state_code,
                                "email": receiver_email,
                                "phone": receiver_phone,
                            }
                        }
                    }
                ]
            })
            header = {
                'POSTE_clientID': "%s" % (company_id.poste_italiane_client_id),
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {0}'.format(company_id.poste_italiane_access_token),
            }

            api_url = "{0}/postalandlogistics/parcel/waybill".format(company_id.poste_italiane_api_url)
            request_type = "POST"
            response_status, response_data = self.poste_italiane_provider_create_shipment(request_type, api_url,
                                                                                          request_data, header)
            if response_status and response_data.get("waybills"):
                tracking_number = []
                for tracking in response_data.get("waybills"):
                    tracking_number.append(tracking.get("code"))
                    url = tracking.get("downloadURL")
                    response = requests.request("GET", url, headers={}, data={})
                    picking.message_post(attachments=[("%s.pdf" % (tracking.get("code")), response.content)])
                shipping_data = {'exact_price': 0.0, 'tracking_number': ','.join(tracking_number)}
                shipping_data = [shipping_data]
                return shipping_data
            else:
                raise ValidationError(response_data)
        except Exception as e:
            raise ValidationError(e)

    def poste_italiane_provider_cancel_shipment(self, picking):
        raise ValidationError("Poate Italiane not provide cancel API.")

    def poste_italiane_provider_get_tracking_link(self, picking):
        return "https://www.poste.it/cerca/#/"
