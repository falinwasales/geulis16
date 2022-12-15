# -*- coding: utf-8 -*-
{
    'name': 'Downpayment Purchase',
    'version': '16.0.0.0.0',
    'license': 'OPL-1',
    'summary': 'Purchase DownPayment',
    'category': 'Purchases',
    'author': 'CLuedoo',
    'website': 'https://www.cluedoo.com',
    'support': 'cluedoo@falinwa.com',
    'description':
    '''
        This module contain some functions:\n
        1. add downpayment on purchase\n
    ''',
    'depends': [
        'purchase'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_views.xml',
        'views/purchase.xml',
        'views/account.xml',
        'wizard/purchase_make_invoice_advance_views.xml',
    ],
    'css': [],
    'js': [],
    'installable': True,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
