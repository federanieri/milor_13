# -*- coding: utf-8 -*-pack
{

    # App information
    'name': 'Poste Italiane Shipping Integration',
    'category': 'Website',
    'version': '13.0.0',
    'summary': """At 𝗩𝗿𝗮𝗷𝗮 𝗧𝗲𝗰𝗵𝗻𝗼𝗹𝗼𝗴𝗶𝗲𝘀, we continue to innovate as a globally renowned 𝘀𝗵𝗶𝗽𝗽𝗶𝗻𝗴 𝗶𝗻𝘁𝗲𝗴𝗿𝗮𝘁𝗼𝗿 𝗮𝗻𝗱 𝗢𝗱𝗼𝗼 𝗰𝘂𝘀𝘁𝗼𝗺𝗶𝘇𝗮𝘁𝗶𝗼𝗻 𝗲𝘅𝗽𝗲𝗿𝘁. Our widely accepted shipping connections are made to easily interface with Odoo, simplifying everything from creating labels to tracking shipments—all from a single dashboard. We’re excited to introduce Poste Italiane Odoo Connectors your one stop solution for seamless global shipping management, now available on the Odoo App Store! At Vraja Technologies, we continue to be at the forefront of Odoo shipping integrations, ensuring your logistics run smoothly across countries. Users also search using these keywords Vraja Odoo Shipping Integration, Vraja Odoo shipping Connector, Vraja Shipping Integration, Vraja shipping Connector, Poste Italiane Odoo Shipping Integration, Poste Italiane Odoo shipping Connector, Poste Italiane Shipping Integration, Poste Italiane shipping Connector, Poste Italiane vraja technologies, Odoo Poste Italiane.""",
    'license': 'OPL-1',

    # Dependencies
    'depends': ['delivery'],

    # Views
    'data': [
        'data/ir_cron.xml',
        'view/res_company.xml',
        'view/delivery_carrier.xml',
        'view/res_country.xml',
    ],
    # Odoo Store Specific
    'images': ['static/description/cover.gif'],

    # Author
    'author': 'Vraja Technologies',
    'website': 'http://www.vrajatechnologies.com',
    'maintainer': 'Vraja Technologies',

    # Technical
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'live_poste_italiane_url': 'https://www.vrajatechnologies.com/contactus',
    'price': '199',
    'currency': 'EUR',

}
# version changelog
