from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
	_inherit = "stock.move.line"

	is_added_from_grouped = fields.Boolean("Is Added From Group", default=False)