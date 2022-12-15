# -*- coding: utf-8 -*-

{
    'name': 'Geulis Product EXT',
    'category': 'geulis',
    'description': """Geulis Product Module EXT.""",
    'depends': ['base','product','sale', 'geulis_purchase_ext','purchase'],
    'data': [
        'data/product_template_data.xml',
        'views/product_view_inherit.xml',
        'views/purchase_order_inherit.xml',
    ],
    'demo':[
        'demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
