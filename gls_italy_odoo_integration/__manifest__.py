{
    'name': 'GLS Italy Shipping Integration',
    'category': 'Website',
    'author': "Vraja Technologies",
    'version': '13.0.2.0',
    'summary': """""",
    'description': """Our Odoo GLS Shipping Integration will help you connect with GLS Shipping Carrier with Odoo. automatically submit order information from Odoo to GLS and get Shipping label, and Order Tracking number from GLS to Odoo.We are providing following modules, Shipping Operations, shipping, odoo shipping integration,odoo shipping connector,marketing integration,dhl,mrw,mondial relay,colissimo.""",
    'depends': ['delivery'],
    'data': [
        'views/res_company.xml',
        'views/delivery_carrier.xml',
    ],
    'images': ['static/description/cover.jpg'],
    'maintainer': 'Vraja Technologies',
    'website': 'www.vrajatechnologies.com',
    'demo': [],
    'live_test_url': 'https://www.vrajatechnologies.com/contactus',
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '199',
    'currency': 'EUR',
    'license': 'OPL-1',
}

# version changelog
# 13.0.0 # Initial version Of App #__ 15/DEC/2020
# 13.0.1 # add cancel shipment features #__ 18/DEC/2020
# 13.0.2 # add tracking features #__23/DEC/2020
# 13.0.3 # fixed cancel features
# 13.0.4 # add product packaging file
# changes in multi packages code
# 13.0.5  change in code check parcel response is instance dict or list
# 13.0.6 add parameter reference and phone number
# 13.0.7 26/01/2024 = add cod functionality
# 16/02/2024 = use replace in phone number
# 08/04/2024 =  one shipment multiple package
# 13/04/2024 = in tracking ref now only one number visible for multi pack
# 16/04/2024 = add "{}".format(receiver_id.phone.replace(' ','') or '') if '+' in receiver_id.phone else "+{}".format(receiver_id.phone.replace(' ','') or '')
