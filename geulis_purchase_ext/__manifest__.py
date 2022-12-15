# -*- coding: utf-8 -*-

{
    'name': 'Geulis Purchase EXT',
    'category': 'geulis',
    'description': """Geulis Purchase Module EXT.""",
    'depends': ['base','purchase','fal_purchase_downpayment','product','stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/vendor_type_view.xml',
        'views/res_partner_vendor.xml',
        'report/report_purchase_order_inherit.xml',
        'report/web_external_layout_inherit.xml',
        'report/job_order.xml',
        'report/job_order_fob.xml',
    ],
    'demo':[
        'demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
