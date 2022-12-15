from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
import logging

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	# def _allowed_group_production(self):
	# 	component_group = self.env.ref('geulis_inventory_ext.components_group').id
	# 	group_id = self.env['res.groups'].search([('id','=',component_group)])
	# 	return group_id

	already_taken = fields.Boolean(string="Already take transfer Move",default=False)
	# allowed_group_id = fields.Many2one('res.groups','Allowed User Group',default=_allowed_group_production, store=True,readonly=True)

	def convert_already_taken(self):
		mrp = self.env['mrp.production'].search([])
		for production in mrp:
			if production.already_taken:
				production.already_taken = False

	@api.depends('move_raw_ids.move_line_ids')
	def _compute_move_line_raw_ids(self):
		for production in self:
			if production.already_taken:
				production.move_line_raw_ids = production.move_raw_ids.move_line_ids
			else:
				production.already_taken = True
				pickings = production.picking_ids
				move = pickings.mapped('move_ids')
				sml = move.mapped('move_line_ids')
				
				for line in production.move_raw_ids.move_line_ids:
					aggrt = 0
					for line2 in sml:
						if line2.product_id == line.product_id and line2.lot_id == line.lot_id:
							aggrt += line2.qty_done
						elif line2.product_id == line.product_id and line2.lot_id != line.lot_id:
							raw = production.move_raw_ids.move_line_ids
							#check if picking is not really part of subcon stock							
							completed = raw.filtered(lambda x:x.product_id == line2.product_id and x.lot_id == line2.lot_id)
							if not completed:
								self.env['stock.move.line'].create({
									'move_id': line.move_id.id,
									'location_id': line.location_id.id,
									'qty_done': line2.qty_done,
									'lot_id': line2.lot_id.id,
									'product_id': line2.product_id.id,
									'product_uom_id': line.product_uom_id.id,
								})
					line.write({
						'qty_done': aggrt,
					})
				production.move_line_raw_ids = production.move_raw_ids.move_line_ids

	def _set_qty_producing(self):
		new_qty_producing = self.product_qty if self.qty_producing != self.product_qty else self.product_qty
		if self.product_id.tracking == 'serial':
			qty_producing_uom = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
			if qty_producing_uom != 1:
				self.qty_producing = self.product_id.uom_id._compute_quantity(1, self.product_uom_id, rounding_method='HALF-UP')

		if not self.already_taken:
			for move in (self.move_raw_ids | self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)):
				if move._should_bypass_set_qty_producing() or not move.product_uom:
					continue
				new_qty = float_round((new_qty_producing - self.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)
				move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
				move.move_line_ids = move._set_quantity_done_prepare_vals(new_qty)
