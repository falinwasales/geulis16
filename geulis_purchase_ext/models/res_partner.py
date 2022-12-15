from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_id = fields.Many2one('vendor.type', string="Vendor Type",ondelete='cascade')
    fal_capacity = fields.Float(string="Capacity")