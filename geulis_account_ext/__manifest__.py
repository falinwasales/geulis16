# -*- coding: utf-8 -*-

{
    'name': 'Geulis Account EXT',
    'category': 'geulis',
    'description': """Geulis Account Module EXT.""",
    'depends': ['base','account','geulis_product_ext','invoice_stock_move'],
    'data': [
        'views/account_view.xml',
    ],
    'demo':[
        'demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
