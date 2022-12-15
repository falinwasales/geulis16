from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    fal_is_purchase_show_downpayment_product = fields.Boolean(
        'Show Downpayment Product in Purchase', help='Show downpayment product to enable user select their downpayment product', default=True)
