# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Nexapp API Sync',
    'license': "LGPL-3",
    'author': "Nexapp srl",
    'website': 'https://nexapp.it/',
    'category': 'Nexapp',
    'version': '13.0.1.0',
    'depends': [
        'base',
        'base_setup',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'wizard/json_preview_wizard_view.xml',
        'wizard/manual_import_json_wizard_view.xml',
        'views/na_api_sync_config_views.xml',
        'views/na_api_sync_log_views.xml',
        'views/na_api_sync_env_views.xml',
        'views/res_config_settings_view.xml'
    ],
    'external_dependencies': {
        'python' : ['ftplib'],
    },
    'installable': True,
}
