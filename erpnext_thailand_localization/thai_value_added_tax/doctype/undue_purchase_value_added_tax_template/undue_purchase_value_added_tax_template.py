# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class UnduePurchaseValueAddedTaxTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		tax_template: DF.Link
	# end: auto-generated types

	pass
