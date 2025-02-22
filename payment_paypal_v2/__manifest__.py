# -*- coding: utf-8 -*-
# Bugid=2187 (This Whole Addon Folder is created under this '2187' bugid)
{
    'name': 'Paypal V2 App for Website',
    'category': 'Payment',
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '12.0',
    'description': """Paypal Payment Acquirer""",
    'author' : "Ankit",
    'depends': ['payment'],
    'license': 'LGPL-3',
    'data': [
        'views/payment_views.xml',
        'views/payment_paypal_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'images': ['static/description/icon.png'],
    'auto_install' : False
}
