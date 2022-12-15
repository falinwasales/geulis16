from odoo.exceptions import UserError
from odoo import models, fields,Command, api, _
from odoo.tools import float_compare, float_is_zero, float_round
import datetime
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    fal_transfer_state = fields.Selection(selection=[
            ('draft', 'Pending'),
            ('confirmed', 'Delivered'),
            ('cancel','Cancel'),
        ], string="Transfer Status", readonly=True, default='draft', compute='_move_transfer_state')
    fal_geulis_discount = fields.Monetary(string="Diskon", currency_field='company_currency_id')
    fal_geulis_discount_khusus = fields.Monetary(string="Diskon Khusus", currency_field='company_currency_id')
    fal_geulis_adm_tokotalk = fields.Monetary(string="Admin TokoTalk", currency_field='company_currency_id')
    fal_geulis_adm_shopee = fields.Monetary(string="Admin Shopee", currency_field='company_currency_id')
    fal_geulis_biaya_pengiriman = fields.Monetary(string="Biaya Pengiriman", currency_field='company_currency_id')
    fal_geulis_poin = fields.Monetary(string="Poin", currency_field='company_currency_id')
    fal_auto_confirm_transfer = fields.Boolean(string="Item is Delivered", help="If this checkbox is ticked,Transfer of this Invoice will be auto confirmed")
    fal_to_proccess = fields.Boolean(string="To Process", default=False, help="This checkbox is information for record that has process with the DO")
    
    @api.model_create_multi
    def create(self, vals_list):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        for val in vals_list:
            if "invoice_line_ids" in val:
                invoice_line = val.get('invoice_line_ids')
                if val.get('fal_geulis_discount') and float_compare(val.get('fal_geulis_discount'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_discount'), 'product_id': self.env.ref('geulis_product_ext.diskon').product_variant_ids[0].id}))
                if val.get('fal_geulis_discount_khusus') and float_compare(val.get('fal_geulis_discount_khusus'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_discount_khusus'), 'product_id': self.env.ref('geulis_product_ext.diskon_khusus').product_variant_ids[0].id}))
                if val.get('fal_geulis_adm_tokotalk') and float_compare(val.get('fal_geulis_adm_tokotalk'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_adm_tokotalk'), 'product_id': self.env.ref('geulis_product_ext.biaya_adm_tokotalk').product_variant_ids[0].id}))
                if val.get('fal_geulis_adm_shopee') and float_compare(val.get('fal_geulis_adm_shopee'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_adm_shopee'), 'product_id': self.env.ref('geulis_product_ext.biaya_adm_shopee').product_variant_ids[0].id}))
                if val.get('fal_geulis_biaya_pengiriman') and float_compare(val.get('fal_geulis_biaya_pengiriman'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_biaya_pengiriman'), 'product_id': self.env.ref('geulis_product_ext.biaya_pengiriman').product_variant_ids[0].id}))
                if val.get('fal_geulis_poin') and float_compare(val.get('fal_geulis_poin'), 0, precision_digits=precision) != 0:
                    invoice_line.append(Command.create({'quantity': 1, 'price_unit': val.get('fal_geulis_poin'), 'product_id': self.env.ref('geulis_product_ext.poin').product_variant_ids[0].id}))
        is_import = self._context.get('import_file')
        res = super(AccountMove, self).create(vals_list)
        counter = 0
        for account_id in res:
            print("Currently doing some automated task")
            counter += 1
            if is_import and not self._context.get('bank_statement'):
                if account_id.move_type == "out_invoice" or account_id.move_type == "in_invoice":
                    account_id.action_post()
                    account_id.action_stock_move()
                    if account_id.fal_auto_confirm_transfer:
                        account_id.invoice_picking_id.action_set_quantities_to_reservation()
                        result = account_id.invoice_picking_id._pre_validate_button()
                        if result:
                            account_id._move_transfer_state()
            print("Finish doing current automated task")
        if counter == len(res):
            print("Finish all automated task")
        return res


    @api.depends('invoice_picking_id.state')
    def _move_transfer_state(self):
        for account in self:
            state_picking = account.invoice_picking_id.state
            if state_picking == 'confirmed':
                account.fal_transfer_state = 'draft'
            elif state_picking == 'done':
                account.fal_transfer_state = 'confirmed'
            elif state_picking == 'cancel':
                account.fal_transfer_state = 'cancel'
            else:
                account.fal_transfer_state = 'draft'


class Picking(models.Model):
    _inherit = "stock.picking"

    # OVERRIDE
    # Need to change all user error method to return false, so the process can keep going at import phase
    def _pre_sanity_check(self, separate_pickings=True):
        """ Sanity check for `button_validate()`
            :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        pickings_without_moves = self.filtered(lambda p: not p.move_ids and not p.move_line_ids)
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        no_quantities_done_ids = set()
        no_reserved_quantities_ids = set()
        for picking in self:
            if all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel'))):
                no_quantities_done_ids.add(picking.id)
            if all(float_is_zero(move_line.reserved_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in picking.move_line_ids):
                no_reserved_quantities_ids.add(picking.id)
        pickings_without_quantities = self.filtered(lambda p: p.id in no_quantities_done_ids and p.id in no_reserved_quantities_ids)

        pickings_using_lots = self.filtered(lambda p: p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots)
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(no_quantities_done_ids, separate_pickings)
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._should_show_transfers():
            if pickings_without_moves:
                return False
                # raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                return False
                # raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                return False
                # raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _('\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
            if message:
                # raise UserError(message.lstrip())
                return False

    def _pre_validate_button(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        if not self.env.context.get('skip_sanity_check', False):
            self._pre_sanity_check()

        self.message_subscribe([self.env.user.partner_id.id])

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()

        if self.user_has_groups('stock.group_reception_report') \
                and self.picking_type_id.auto_show_reception_report:
            lines = self.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search([('id', 'child_of', self.picking_type_id.warehouse_id.view_location_id.id), ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                        ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                        ('product_qty', '>', 0),
                        ('location_id', 'in', wh_location_ids),
                        ('move_orig_ids', '=', False),
                        ('picking_id', 'not in', self.ids),
                        ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = self.action_view_reception_report()
                    action['context'] = {'default_picking_ids': self.ids}
                    return action
        return True