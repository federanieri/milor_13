# -*- coding: utf-8 -*-
{
    'name': "FTPFilesManager",

    'summary': """
        Download PDF files with FTP""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Rapsodoo",
    'website': "http://www.rapsodoo.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','syd_os1'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/cron_job_ftp.xml',
        'views/ftp_configuration.xml'
    ],    
    'license': 'LGPL-3',
    'installable':True,
    'application':False,
    'auto_install':True
}
