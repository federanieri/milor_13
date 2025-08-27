import pytz
import json

from odoo import models, fields, api, _

utc = pytz.utc


class ShopifyOrderDataQueueLineEpt(models.Model):
    _inherit = "shopify.order.data.queue.line.ept"

    def create_order_data_queue_line(self, order_ids, instance, created_by='import'):
        res = super().create_order_data_queue_line(order_ids, instance, created_by='import')

        if len(res) >= 1:
            shopify_order = self.env['shopify.order.data.queue.ept'].search([('id', '=', res[0])])
            # ciclo tutte le righe appena create
            for order_line in shopify_order.order_data_queue_line_ids:

                # trasformo in dizionario i dati
                order_response = json.loads(order_line.order_data)

                # verifico che ai campi della sorgente e del codice non sia assegnato nulla e nel caso li valorizzo
                if order_response.get('order')['shipping_lines']:
                    if not order_response.get('order')['shipping_lines'][0]['source']:
                        order_response.get('order')['shipping_lines'][0]['source'] = 'shopify'
                    if not order_response.get('order')['shipping_lines'][0]['code']:
                        order_response.get('order')['shipping_lines'][0]['code'] = 'standard'

                # trasofrmo i dati dell'ordine in stringa e li re-inserisco in order_data
                order_line.order_data = json.dumps(order_response)

        return res