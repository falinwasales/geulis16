from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        quantity = stock_move.quantity_done
        res = super()._prepare_stock_return_picking_line_vals_from_move(stock_move)
        res.update({'quantity':quantity})
        return res

    def _search_origin_picking(self,new_picking_id):
        new_picking = self.env["stock.picking"].search([("id","=",new_picking_id)])
        old_name_origin = new_picking.origin.rsplit("Return of ")[1]
        old_picking_id = self.env["stock.picking"].search([("name","=",old_name_origin)])
        sml_origin = old_picking_id.move_line_ids
        domain = [
            ('picking_id', '=', old_picking_id.id)
        ]
        #Compare between old picking move line and new picking move line
        #to determine which lot belong to which move line
        grouped = sml_origin.read_group(domain,['qty_done'],['product_id','lot_id'],lazy=False)
        for sml in new_picking.move_line_ids:
            for g in grouped:
                if 'taken' in g:
                    continue
                sml_value = float_round(sml.reserved_uom_qty,precision_digits=2,rounding_method='HALF-UP')
                g_value = float_round(g['qty_done'],precision_digits=2,rounding_method='HALF-UP')
                if sml.product_id.id == g['product_id'][0] and sml_value == g_value:
                    if sml.lot_id.id == g['lot_id']:
                        sml.qty_done = sml.reserved_uom_qty
                    else:
                        sml.lot_id = g['lot_id']
                        sml.qty_done = sml.reserved_uom_qty
                    g.update({'taken': True})
                    break
        return True

    def create_returns(self):
        res = super().create_returns()
        self._search_origin_picking(res['res_id']) 
        return res