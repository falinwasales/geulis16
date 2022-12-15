from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fal_due_date_payment = fields.Date(string='Due Date Payment')

    def get_downpayment_product(self):
        prod_id = self.env['ir.config_parameter'].sudo().get_param('fal_purchase_downpayment.fal_deposit_product_id')
        downpayment = self.env['product.product'].search([('id','=',prod_id)]).name
        return downpayment

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    dpInPercent = fields.Float(string='DP %')
    cutting_qty = fields.Float(string='Cutting Qty',default=0)

class PurchaseAdvancePaymentInv(models.TransientModel):
    _inherit = 'purchase.advance.payment.inv'

    def create_invoices(self):
        account_move =  self.env['account.move'].browse(self._context.get('fal_invoice_id', []))
        purchase_orders = self.env['purchase.order'].browse(self._context.get('active_ids', []))
        account_move.unlink()

        if self.advance_payment_method == 'received':
            purchase_orders.with_context(journal_id=self.journal_id.id)._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('fal_purchase_downpayment.fal_deposit_product_id', self.product_id.id)

            purchase_line_obj = self.env['purchase.order.line']
            for order in purchase_orders:
                amount, name = self._get_advance_details(order)
                if self.product_id.purchase_method != 'purchase':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.supplier_taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}

                so_line_values = self._prepare_po_line(order, tax_ids, amount)
                so_line_values.update({
                    'dpInPercent' : self.amount
                })
                po_line = purchase_line_obj.create(so_line_values)
                del context
                self._create_invoice(order, po_line, amount)
        if self._context.get('open_invoices', False):
            return purchase_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}