from odoo import models, fields
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
	_inherit = "purchase.order"

	def _determine_correct_index(self,attributes):
		ref_name_size = None
		ref_name_color = None

		for attribute in range(len(attributes)):
			if attributes[attribute].attribute_id.name.lower() == "size":
				ref_name_size = attribute
			if attributes[attribute].attribute_id.name.lower() == "color":
				ref_name_color = attribute

		return ref_name_color,ref_name_size

	def groupEveryProduct(self):
		result = []
		product_quantity = dict()
		product_comp_color = []
		product_comp_dict = {
			'color' : "",
			'component': []
		}
		#Create dictionary of product, color, and component of its BOM
		#dictionary is unique based on color
		for product in self.order_line.filtered(lambda x:x.product_id.name !='Vendor Down payment'):
			for bom in product.product_id.bom_ids.filtered(lambda x:x.product_id.id==product.product_id.id):
				for bom_line in bom.bom_line_ids:
					if product.product_id.product_template_attribute_value_ids:
						index = self._determine_correct_index(product.product_id.product_template_attribute_value_ids.attribute_line_id)
						if product.product_id.product_template_attribute_value_ids[index[0]].name not in product_comp_color:
							product_comp_name = []
							pmk = []
							product_comp_name.append(bom_line.product_id)
							pmk.append(bom_line.product_qty)
							product_comp_color.append(product.product_id.product_template_attribute_value_ids[index[0]].name)
							result.append({
								"color" : product.product_id.product_template_attribute_value_ids[index[0]].name,
								"component": product_comp_name,
								"pmk": pmk	
							})
						else:
							idx = product_comp_color.index(product.product_id.product_template_attribute_value_ids[index[0]].name)
							if bom_line.product_id not in result[idx]['component']:
								result[idx]['component'].append(bom_line.product_id)
								result[idx]['pmk'].append(bom_line.product_qty)
					else:
						raise UserError("Product doesn't have color variant")		
		return result


	def groupAllSize(self,color):
		product_size = dict()
		idx = self._determine_correct_index(self.order_line.mapped('product_id').product_template_attribute_value_ids.attribute_line_id)
		for product in self.order_line.filtered(lambda x:x.product_id.name !='Vendor Down payment' and x.product_id.product_template_attribute_value_ids and x.product_id.product_template_attribute_value_ids[idx[0]].name==color):
			if product.product_id.product_template_attribute_value_ids:
				try:
					if product.product_id.product_template_attribute_value_ids[idx[1]].name not in product_size:
						product_size.update({
							product.product_id.product_template_attribute_value_ids[idx[1]].name : product.product_qty
						})
					else:
						product_size[product.product_id.product_template_attribute_value_ids[idx[1]].name] +=  product.product_qty
				except IndexError as e:
					_logger.info("Product doesn't have color variant")
		return product_size


	def searchLongestSizeVar(self):
		#Return a unique list of size
		#Example [XS, S, M, L, XL, XXL]
		longest_size_var = 0
		sizes = []
		product_comp_name = self.groupEveryProduct()
		for val in product_comp_name:
			size_group = dict()
			size_group = self.groupAllSize(val['color'])
			sizes += size_group.keys()
		return self.unique(sizes)

	def TotQtySize(self):
		product_comp_name = self.groupEveryProduct()
		size_list = self.searchLongestSizeVar()
		sizes_qty = dict()
		for size in size_list:
			sizes_qty.update({
				size : 0
			})
		idx = self._determine_correct_index(self.order_line.mapped('product_id').product_template_attribute_value_ids.attribute_line_id)
		for val in product_comp_name:
			for product in self.order_line.filtered(lambda x:x.product_id.name !='Vendor Down payment' and x.product_id.product_template_attribute_value_ids[idx[0]].name==val['color']):
				try:
					if product.product_id.product_template_attribute_value_ids[idx[1]].name not in sizes_qty:
						sizes_qty.update({
							product.product_id.product_template_attribute_value_ids[idx[1]].name : product.product_qty
						})
					else:
						sizes_qty[product.product_id.product_template_attribute_value_ids[idx[1]].name] +=  product.product_qty
				except IndexError as e:
					_logger.info("Product doesn't have color variant")
		return sizes_qty

			
	def showSize(self,color):
		limit = len(self.searchLongestSizeVar())
		idx_list = list(self.searchLongestSizeVar())
		list_size_value = [0]*limit
		# data = self.groupAllSize(color).values()
		data = self.groupAllSize(color)
		# data = list(data)
		for k,i in data.items():
			idx = idx_list.index(k)
			list_size_value[idx] = i

		return list_size_value

	def unique(self,list1):
		# initialize a null list
		unique_list = []
		# traverse for all elements
		for x in list1:
			# check if exists in unique_list or not
			if x not in unique_list:
				unique_list.append(x)
		result = self.get_id_color()
		sorted_unique_list = self.sorted_dict_size(unique_list,result)
		sorted_result = []
		for sort in sorted_unique_list:
			 sorted_result.append(sort[0])
		return sorted_result

	def get_id_color(self):
		# Mapping every size with their sequence or id so they can be sorted 
		# Example [XS=1, S=2, M=3, L=4, XL=5, XXL=6]
		color_id_dict = dict()
		product = self.order_line.mapped("product_template_id")
		list_sizes = product.attribute_line_ids.filtered(lambda x:x.attribute_id.name.lower() == 'size').value_ids
		if sum(list_sizes.mapped('sequence')) > 0:
			for list_size in list_sizes:
				color_id_dict.update({
					list_size.name : list_size.sequence
				})
		else:
			for list_size in list_sizes:
				color_id_dict.update({
					list_size.name : list_size.id
				})
		return color_id_dict

	def sorted_dict_size(self,list_size,ref_size):
		result = dict()
		for size in list_size:
			result.update({
				size: ref_size.get(size)
			})
		return sorted(result.items(), key=lambda item: item[1])


	def get_color_code(self,comp):
		index = self._determine_correct_index(comp.product_template_attribute_value_ids.attribute_line_id)
		str_of_color = comp.product_template_attribute_value_ids[index[0]].name
		res = str_of_color.rsplit("#")
		return res