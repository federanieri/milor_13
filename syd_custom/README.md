# odoo13_milor(syd_custom)

#INTO Models.py

shopify_instance_name is a variable that has shopify.instance as its key and returns the string 'BRONZALLUREIT'
shopify_payment_gateway_name is a variable that has as key shopify.payment.gateway and as value the string 'Cash on Delivery (COD)'
carrier_id is a variable that is present in the delivery.carrier table and in line 1860 .search finds the key 'carrier.name' and as value 'GLS CONTRASSEGNO '
[1857] if self.shopify_instance_id.name == shopify_instance_name:    if 'BRONZALLUREIT' == 'BRONZALLUREIT':
[1858]         if self.shopify_payment_gateway_id.name == shopify_payment_gateway_name:         if 'Cash on Delivery (COD)' == 'Cash on Delivery (COD)':