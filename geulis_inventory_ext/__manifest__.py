# -*- coding: utf-8 -*-

{
    'name': 'Geulis Inventory EXT',
    'category': 'geulis',
    'description': """Geulis Inventory Module EXT.""",
    'depends': ['base','stock','stock_picking_batch','mrp','mrp_subcontracting','product','geulis_product_ext'],
    'data': [
        'data/inventory_user_group.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_batch_form.xml',
        'views/geulis_move_line_form.xml',
        'views/stock_lot_tree_inherit.xml',
        'views/mrp_production_view_finished.xml',
        'views/mrp_production_view_component.xml',
        'views/mrp_production_view_base_group.xml',
        'views/stock_move_view.xml',
        'views/mrp_view_finished.xml',
        'views/mrp_view_component.xml',
    ],
    'demo':[
        'demo.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
