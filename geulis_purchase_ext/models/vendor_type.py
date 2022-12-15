from odoo import models, fields

class VendorType(models.Model):
    _name = "vendor.type"
    _description = "Vendor Type"
    _rec_name = "fal_vendor_type"

    fal_vendor_type = fields.Char(string="Vendor Type", required=True)
    vendors_line = fields.One2many('res.partner','vendor_id',string="Vendors Line")

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s' % (rec.fal_vendor_type)))
        return res