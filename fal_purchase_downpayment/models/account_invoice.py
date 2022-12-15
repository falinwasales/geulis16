# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    fal_downpayment_auto_complete = fields.Many2one('purchase.order', string='Downpayment Auto Complete', domain="[('partner_id', '=', partner_id)]")

    def unlink(self):
        downpayment_lines = self.mapped('line_ids.purchase_line_id').filtered(lambda line: line.fal_is_downpayment)
        res = super(AccountMove, self).unlink()
        for downpayment_line in downpayment_lines:
            # As we can't use odoo unlink (Blocked by the purchase state, we need to force it by cr)
            query = """
                DELETE FROM purchase_order_line
                WHERE id = %s""" % downpayment_line.id
            self.env.cr.execute(query)
        return res

    def button_action(self):
        view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'fal_purchase_downpayment.view_purchase_advance_payment_inv'
        )
        context = self.env.context.copy()
        context.update({'company_id': self.company_id.id,'active_ids':[self.fal_downpayment_auto_complete.id],'active_id':self.fal_downpayment_auto_complete.id,'fal_invoice_id': self.id})
        view = {
            'name': _('Down Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.advance.payment.inv',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'readonly': True,
            'context': context
        }
        return view
