from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class Picking(models.Model):
	_inherit = "stock.picking"

	def button_validate(self):
		res = super(Picking,self).button_validate()
		if self.picking_type_id.code == "incoming":
			po = self.purchase_id or False
			if po:
				for line in po.order_line:
					po.received_qty += line.qty_received
		return res