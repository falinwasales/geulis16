from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPickingBatch(models.Model):
	_inherit = "stock.picking.batch"

	move_line_grouped_by_product = fields.One2many('stock.move.line.grouped.by.product','batch_id', string='Stock Move Product Group', readonly=True)

	def action_group(self):
		StockGroupedByProduct = self.env['stock.move.line.grouped.by.product']
		StockMoveLine = self.env['stock.move.line']
		domain = [
			('batch_id', '=', self.id)
		]
		grouped = StockMoveLine.read_group(domain, ['qty_done'], ['product_id'])
		for g in grouped:
			product_exist = StockGroupedByProduct.search([("batch_id.id","=",self.id),("product_id","=",g['product_id'][0])])
			lot_ids = StockMoveLine.search([("batch_id.id","=",self.id),("product_id","=",g['product_id'][0])]).mapped('lot_id')
			lot_ids_arr = [lot.id for lot in lot_ids]
			if product_exist:
				product_exist.with_context({'is_lot_group': False}).write({
					'total': g['qty_done'],
					'lot_ids': [(6, 0, lot_ids_arr)]
				})
			else:
				StockGroupedByProduct.create({
					'product_id': g['product_id'][0],
					'batch_id': self.id,
					'total': g['qty_done'],
					'lot_ids': [(6, 0, lot_ids_arr)],
				})

	def reset(self,product=None):
		# Reset all stock move line in batch transfer by setting its qty to zero and delete it if it's custom made
		# or set its qty to zero and delete it if it's made by odoo/system and its reserved is zero   
		if product:
			move_lines = self.move_line_ids.filtered(lambda x:x.product_id==product)
		else:
			move_lines = self.move_line_ids
		for stock_picking in move_lines:
			if stock_picking.is_added_from_grouped:
				stock_picking.qty_done = 0
				stock_picking.unlink()
			else:
				if stock_picking.reserved_uom_qty == 0:
					stock_picking.qty_done = 0
					stock_picking.unlink()
				else:
					stock_picking.qty_done = 0


class StockGroupedByProduct(models.Model):
	_name = "stock.move.line.grouped.by.product"
	_description = "Stock move line group by product or product lot"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
	batch_id = fields.Many2one('stock.picking.batch','Batch',ondelete="cascade")
	total = fields.Float(string="Total", default=0.0)
	lot_ids = fields.Many2many('stock.lot','stock_group_lot_rel','lot_id','stock_grouped_id',string="List of all lot")
	deman_per_product = fields.Float(string="Total demand", compute="_compute_total_demand")
	company_id = fields.Many2one(
		'res.company', string="Company", required=True, readonly=True,
		index=True, default=lambda self: self.env.company)
	move_line_grouped_by_lot = fields.One2many('stock.move.line.grouped.by.lot','grouped_by_product_id', string='Stock By Lot', readonly=False)
	current_total = fields.Float(string="Current Total",default=0.0, readonly=True,compute="_change_current_total")

	@api.depends('move_line_grouped_by_lot.total_lot')
	def _change_current_total(self):
		current = 0
		for grouped_by_lot in  self.move_line_grouped_by_lot:
			current += grouped_by_lot.total_lot
		self.current_total = current

	@api.depends('batch_id.move_ids')
	def _compute_total_demand(self):
		demand = self.batch_id.move_ids.filtered(lambda x:x.product_id.id == self.product_id.id).mapped("product_uom_qty")
		self.deman_per_product = sum(demand)

	def lot_group_wizard(self):
		stock_prod = self.env['stock.move.line.grouped.by.product'].search([('product_id','=',self._context.get("product_id")),('batch_id','=',self._context.get("batch_id"))])
		StockGroupedByLot = self.env['stock.move.line.grouped.by.lot']
		view = self.env.ref('geulis_inventory_ext.stock_batch_grouped_product')
		is_lot_not_exist = True if stock_prod.product_id.tracking == 'none' else False
		if is_lot_not_exist:
			domain = [
				('product_id','=',self._context.get("product_id")),
				('grouped_by_product_id.id','=',self._context.get("id")),
			]
			data = StockGroupedByLot.search(domain)
			if not data:
					StockGroupedByLot.create({
						'product_id': self._context.get('product_id'),
						'lot_id': False,
						'total_lot' : 0,
						'grouped_by_product_id' : self._context.get("id")
					})
			else:
				data.write({
					'grouped_by_product_id' : self._context.get("id")
				})
		else:
			for lot in self._context.get("lot_ids")[0][2]:
				domain = [
					('product_id','=',self._context.get("product_id")),
					('grouped_by_product_id.id','=',self._context.get("id")),
					('lot_id.id','=',lot)
				]
				data = StockGroupedByLot.search(domain)
				if not data:
					StockGroupedByLot.create({
						'product_id': self._context.get('product_id'),
						'lot_id': lot,
						'total_lot' : 0,
						'grouped_by_product_id' : self._context.get("id")
					})
				else:
					data.write({
						'grouped_by_product_id' : self._context.get("id")
					})
		return {
			'name': _('Form'),
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'stock.move.line.grouped.by.product',
			'views': [(view.id, 'form')],
			'view_id': view.id,
			'target': 'new',
			'res_id': stock_prod.id,
			'context': {
				"is_lot_not_exist" : is_lot_not_exist,
			}
		}

	#Distribute every total of lot to every RES that has same product
	def _compute_value(self):
		lot_total = []
		StockGroupedByLot = self.env['stock.move.line.grouped.by.lot'].search([('grouped_by_product_id','=',self.id)])
		if not StockGroupedByLot:
			raise UserError(_("No Stock Group By Lot Found!"))	
		for stock in StockGroupedByLot.sorted(lambda x:x.total_lot, reverse=True):
			lot_total.append({
				'lot' : stock.lot_id,
				'total': stock.total_lot,
			})
		lot_total_count = len(lot_total)

		stock_move_line = self.env['stock.move.line'].search([('batch_id','=',self.batch_id.id),('product_id','=',self.product_id.id)])
		count = 0
		for stock in stock_move_line:
			tmp_total = lot_total[count]['total'] - stock.reserved_uom_qty
			if tmp_total < 0:
				stock.write({
					'lot_id': lot_total[count]['lot'].id,
					'qty_done' : abs(lot_total[count]['total']),
				})
				lot_total[count]['total'] = 0
				count += 1
				if count > lot_total_count-1:
					break
				move = stock.move_id
				prepared_value_line = {
					'move_id' : move.id,
					'product_id' : stock.product_id.id,
					'picking_id' : stock.picking_id.id,
					'lot_id' : lot_total[count]['lot'].id,
					'lot_name' : lot_total[count]['lot'].name,
					'owner_id' : stock.owner_id.id,
					'location_id' : stock.location_id.id,
					'location_dest_id' : stock.location_dest_id.id,
					'company_id' : stock.company_id.id,
					'product_uom_id' : stock.product_uom_id.id,
					'qty_done' : abs(tmp_total) if lot_total[count]['total'] - abs(tmp_total) >= 0 else lot_total[count]['total'],
					'is_added_from_grouped' : True,
					'batch_id': stock.batch_id.id,
				}
				# self.env['stock.move.line'].create(prepared_value_line)
				# lot_total[count]['total'] -= abs(tmp_total)
				res = self.env['stock.move.line'].create(prepared_value_line)
				lot_total[count]['total'] -= abs(tmp_total)
				if lot_total[count]['total'] <= 0:
					remaining = abs(lot_total[count]['total'])
					count+=1
					# This loops stop when the next lot still has quantity to be assign to next stock move line
					while count <= lot_total_count-1:
						if lot_total[count]['total'] >= remaining:
							lot_total[count]['total'] -= remaining
							prepared_value_line = {
								'move_id' : move.id,
								'product_id' : stock.product_id.id,
								'picking_id' : stock.picking_id.id,
								'lot_id' : lot_total[count]['lot'].id,
								'lot_name' : lot_total[count]['lot'].name,
								'owner_id' : stock.owner_id.id,
								'location_id' : stock.location_id.id,
								'location_dest_id' : stock.location_dest_id.id,
								'company_id' : stock.company_id.id,
								'product_uom_id' : stock.product_uom_id.id,
								'qty_done' : remaining,
								'is_added_from_grouped' : True,
								'batch_id': stock.batch_id.id,
							}
							res = self.env['stock.move.line'].create(prepared_value_line)
							break
						else:
							prepared_value_line = {
								'move_id' : move.id,
								'product_id' : stock.product_id.id,
								'picking_id' : stock.picking_id.id,
								'lot_id' : lot_total[count]['lot'].id,
								'lot_name' : lot_total[count]['lot'].name,
								'owner_id' : stock.owner_id.id,
								'location_id' : stock.location_id.id,
								'location_dest_id' : stock.location_dest_id.id,
								'company_id' : stock.company_id.id,
								'product_uom_id' : stock.product_uom_id.id,
								'qty_done' : lot_total[count]['total'],
								'is_added_from_grouped' : True,
								'batch_id': stock.batch_id.id,
							}
							res = self.env['stock.move.line'].create(prepared_value_line)
							remaining -= lot_total[count]['total']
							lot_total[count]['total'] = 0
						count+=1

			else:
				lot_total[count]['total'] = tmp_total
				stock.write({
					'lot_id': lot_total[count]['lot'].id,
					'qty_done' : stock.reserved_uom_qty,
				})

		#Perform a check process to look for ramaining quantity and add it to
		#move line accordingly or make new move line if not found
		self._check_total_remain(lot_total,self.product_id,self.batch_id)
		self.batch_id.action_group()

	def _check_total_remain(self,lot_total,product_id,batch_id):
		domain = [
			('batch_id.id', '=', batch_id.id),
			('product_id.id', '=', product_id.id)
		]
		for arr in lot_total:
			if arr['total'] <= 0:
				continue
			if product_id.tracking != 'none':
				domain += [('lot_id.id', '=', arr['lot'].id)]
			stock = self.env['stock.move.line'].search(domain,order="picking_id desc",limit=1)
			if stock:
				stock.write({
					'qty_done' : stock.qty_done+arr['total']
				})
				domain.pop()
			else:
				domain.pop()
				stock = self.env['stock.move.line'].search(domain,order="picking_id desc",limit=1)
				prepared_value_line = {
					'move_id' : stock.move_id.id,
					'product_id' : stock.product_id.id,
					'picking_id' : stock.picking_id.id,
					'lot_id' : arr['lot'].id,
					'lot_name' : arr['lot'].name,
					'owner_id' : stock.owner_id.id,
					'location_id' : stock.location_id.id,
					'location_dest_id' : stock.location_dest_id.id,
					'company_id' : stock.company_id.id,
					'product_uom_id' : stock.product_uom_id.id,
					'qty_done' : arr['total'],
					'batch_id': stock.batch_id.id,
					'is_added_from_grouped' : True,
				}
				res = self.env['stock.move.line'].create(prepared_value_line)

	#Override write method to saperate between saving at product grouping and lot grouping
	def write(self,vals):
		# stock_move_line = self.env['stock.move.line'].search([('batch_id','=',self.batch_id.id),('product_id','=',self.product_id.id)])
		stock = super(StockGroupedByProduct,self).write(vals)
		if self._context.get('is_lot_group'):
			# for stock in stock_move_line:
			# 	if stock.is_added_from_grouped:
			# 		stock.unlink()
			self.batch_id.action_assign()
			self.batch_id.reset(product=self.product_id)
			self._compute_value()
		stock_move_line = self.batch_id.move_line_ids.filtered(lambda x:x.reserved_uom_qty == 0 and x.qty_done == 0)
		stock_move_line.unlink()
		return stock

	def close_window(self):
		return {'type': 'ir.actions.act_window_close'}

class StockGroupedByLot(models.Model):
	_name = "stock.move.line.grouped.by.lot"
	_description = "Stock move line group by product or product lot"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
	total_lot = fields.Float(string="Total Lot",digits = (12,4))
	lot_id = fields.Many2one(
		'stock.lot', 'Lot/Serial Number',
		domain="[('product_id', '=', product_id), ('company_id', '=', company_id),('quant_ids.location_id.location_id.name','=','LG')]", check_company=True)
	company_id = fields.Many2one(
		'res.company', string="Company", required=True, readonly=True,
		index=True, default=lambda self: self.env.company)
	grouped_by_product_id = fields.Many2one('stock.move.line.grouped.by.product',string='Stock Product ID')

	@api.onchange("product_id")
	def set_default_product(self):
		self.product_id = self.grouped_by_product_id.product_id.id

	@api.constrains("lot_id")
	def _check_if_lot_exist(self):
		for lot in self:
			if not lot.lot_id and lot.product_id.tracking != 'none':
				is_exist = self.env['stock.lot'].search([('product_id','=',lot.product_id.id)])
				if is_exist:
					raise UserError(_("You Must Assign a Lot/Serial Number to a Tracked Product"))
	
class StockProductionLot(models.Model):
	_inherit="stock.lot"

	oh = fields.Float(string="On Hand Quantity", compute="_compute_quantity")
	aq = fields.Float(string="Available Quantity", compute="_compute_quantity")

	def _compute_quantity(self):
		for stock in self:
			stock.oh = stock.quant_ids.filtered(lambda x:x.product_id == stock.product_id and x.location_id.usage in ['internal'] and x.location_id.location_id.name == 'LG').quantity
			stock.aq = stock.quant_ids.filtered(lambda x:x.product_id == stock.product_id and x.location_id.usage in ['internal'] and x.location_id.location_id.name == 'LG').available_quantity

	def name_get(self):
		result = []
		for rec in self:
			total_available = rec.quant_ids.filtered(lambda x:x.product_id == rec.product_id and x.location_id.usage in ['internal'] and x.location_id.location_id.name == 'LG').available_quantity
			total_on_hand = rec.quant_ids.filtered(lambda x:x.product_id == rec.product_id and x.location_id.usage in ['internal'] and x.location_id.location_id.name == 'LG').quantity
			formatted_total_available = "{:.4f}".format(total_available)
			formatted_total_quantity = "{:.4f}".format(total_on_hand)
			# name = rec.name + '( AQ: ' + str(formatted_total_available) + ' Q: ' + str(formatted_total_quantity) + ' )'
			name = rec.name + ' Q: ' + str(formatted_total_quantity)
			result.append((rec.id, name))
		return result


class StockMove(models.Model):
	_inherit="stock.move"

	def action_show_details(self):
		""" Open the produce wizard in order to register tracked components for
		subcontracted product. Otherwise use standard behavior.
		"""
		self.ensure_one()
		if self._subcontrating_should_be_record() or self._subcontrating_can_be_record():
			return self._action_record_components()
		action = super(StockMove, self).action_show_details()
		if self.is_subcontract and all(p._has_been_recorded() for p in self._get_subcontract_production()):
			if self.env.user.has_group('geulis_inventory_ext.components_group'):
				action['views'] = [(self.env.ref('geulis_inventory_ext.view_stock_move_operations_group_component').id, 'form')]
			elif self.env.user.has_group('base.group_user'):
				action['views'] = [(self.env.ref('geulis_inventory_ext.view_stock_move_operations_group_base').id, 'form')]
			else:
				action['views'] = [(self.env.ref('stock.view_stock_move_operations_group_finished').id, 'form')]
			action['context'].update({
				'show_lots_m2o': self.has_tracking != 'none',
				'show_lots_text': False,
			})
		return action

	def _action_record_components(self):
		self.ensure_one()
		view = False
		production = self._get_subcontract_production()[-1:]
		if self.env.user.has_group('geulis_inventory_ext.finished_goods_group'):
			view = self.env.ref('geulis_inventory_ext.mrp_production_subcontracting_form_view_finished')
		elif self.env.user.has_group('geulis_inventory_ext.components_group'):
			view = self.env.ref('geulis_inventory_ext.mrp_production_subcontracting_form_view_component')
		else:
			view = self.env.ref('geulis_inventory_ext.mrp_production_subcontracting_form_view_base')
		return {
			'name': _('Subcontract'),
			'type': 'ir.actions.act_window',
			'view_mode': 'form',
			'res_model': 'mrp.production',
			'views': [(view.id, 'form')],
			'view_id': view.id,
			'target': 'new',
			'res_id': production.id,
			'context': self.env.context,
		}
