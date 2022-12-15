from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError

class Product(models.Model):
    _inherit = 'product.template'

    fal_release_date = fields.Date(string='Release Date',default=datetime.today())
    fal_designer = fields.Char(string='Designer')
    fal_vendor_cmt = fields.Many2one('res.partner',string='Vendor CMT',domain="[('supplier_rank','>',0),('vendor_id.fal_vendor_type','=','CMT')]")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    fal_product_code = fields.Char(string='Product Variant Code')
    fal_product_age = fields.Integer(string="Age",compute="_compute_product_age")
    fal_product_status = fields.Selection([
            ('new','New'),
            ('discount','Discount'),
            ('maintain','Maintain'),
            ('sale','Sale'),
            ('not_sale','Not4Sale')
        ],string="Status",default='new')
    fal_last_percen_sale = fields.Float(string="Last Sale %")
    fal_stock_maintain = fields.Float(string="Stock to be Maintain")
    fal_display_category = fields.Selection([
            ('best','Best Selling'),('new','New Arrival'),('sale','Sale'),('unknown','Undefined'),('hide','Hide')
        ],string="Display Category", default="new")
    fal_bin_capacity = fields.Float(string="Kapasitas per Bin")
    fal_bin_to_be_maintained = fields.Float(string="Jumlah Bin to be maintain")

    def _compute_product_age(self):
        fmt = '%Y-%m-%d'
        current_date = datetime.today().date()
        for product in self:
            release_date = product.fal_release_date
            d1 = datetime.strptime(str(release_date), fmt)
            d2 = datetime.strptime(str(current_date), fmt)
            date_difference = d2 - d1
            product.fal_product_age = date_difference.days