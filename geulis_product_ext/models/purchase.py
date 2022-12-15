from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fal_purchase_type = fields.Selection([
        ('product', 'Pembelian Barang'),
        ('service', 'Pembelian Jasa'),
    ], string='Tipe Pembelian', required=True, default='product')
    fal_comment_marketing = fields.Selection([
        ('new', 'New'),
        ('repeat', 'Repeat'),
    ], string='Comment Marketing', default='new')
    fal_brand = fields.Selection([
        ('geulis', 'Geulis'),
        ('kasep', 'Kasep'),
    ], string='Brand', default='geulis')
    qty_jo = fields.Float(string='Quantity JO', default=0, readonly=True, compute="_compute_data_qty_jo",store=True)
    cutting_qty = fields.Float(string='Quantity Cutting', default=0, readonly=True, compute="_compute_cutting_qty",store=True)
    received_qty = fields.Float(string='Quantity Received', readonly=True)
    fal_product_template_id = fields.Many2one('product.template', string='Product', compute='_get_product_info')
    fal_release_date = fields.Datetime(string='Product Release Date', compute='_get_product_info', store=True)

    @api.depends('order_line','fal_purchase_type')
    def _compute_data_qty_jo(self):
        total_qty = 0
        for purchase in self:
            if purchase.fal_purchase_type == 'product':
                continue
            for line in purchase.order_line:
                total_qty += line.product_qty
            purchase.qty_jo = total_qty
        else:
            pass

    @api.depends('order_line.cutting_qty','fal_purchase_type')
    def _compute_cutting_qty(self):
        total_cuttin_qty = 0
        for purchase in self:
            for line in purchase.order_line:
                total_cuttin_qty += line.cutting_qty
            purchase.cutting_qty = total_cuttin_qty

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        self_comp = self.with_company(company_id)
        res = super(PurchaseOrder, self_comp).create(vals)

        if vals.get('fal_purchase_type') == 'service':
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            res.name = self.env['ir.sequence'].\
                    next_by_code('job.order', sequence_date=seq_date) or 'New'
        return res

    @api.depends('order_line.product_template_id')
    def _get_product_info(self):
        for purchase in self:
            if purchase.order_line:
                pt = purchase.order_line.mapped('product_template_id')
                release_date = pt.mapped('fal_release_date')
                purchase.fal_release_date = release_date[0]
                purchase.fal_product_template_id = pt[0]
            else:
                purchase.fal_release_date = False
                purchase.fal_product_template_id = False