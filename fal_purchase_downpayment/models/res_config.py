# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fal_deposit_product_id = fields.Many2one(
        'product.product',
        string="Down Payments",
        domain="[('type', '=', 'service'), ('purchase_method', '=', 'purchase')]",
        help='Default product used for payment advances'
    )

    fal_is_purchase_show_downpayment_product = fields.Boolean(related="company_id.fal_is_purchase_show_downpayment_product", readonly=False,
        string='Show Downpayment Product in Purchase', help='Show downpayment product to enable user select their downpayment product')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        fal_deposit_product_id = literal_eval(ICPSudo.get_param(
            'fal_purchase_downpayment.fal_deposit_product_id',
            default='False'))
        if fal_deposit_product_id and not self.env['product.product'].browse(
                fal_deposit_product_id).exists():
            fal_deposit_product_id = False
        res.update(
            fal_deposit_product_id=fal_deposit_product_id,
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param(
            "fal_purchase_downpayment.fal_deposit_product_id",
            self.fal_deposit_product_id.id)
        return res
