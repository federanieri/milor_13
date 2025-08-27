# -*- encoding: utf-8 -*-
##############################################################################
#
#    
#
##############################################################################

{
    'name': 'Ifs Region',
    'version': '0.1',
    'category': 'Generic Modules/Others',
    'description': """Migrazione per BEC""",
    'author': 'Infosons',
    'website': 'http://www.infosons.com',
    'depends': ['base','contacts'],
    'data': [
        'data/res.region.csv',
        'data/res.country.state.csv',
        'security/ir.model.access.csv',
        'views.xml'
        ],
    'license': 'LGPL-3',
    'installable': True,
    'active': False,
}
