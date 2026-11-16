# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PP30Branch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_number: DF.Data | None
		branch_no: DF.Data
		exempt_sales: DF.Currency
		input_vat: DF.Currency
		output_vat: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		postal_code: DF.Data | None
		purchase_amount: DF.Currency
		sales_amount: DF.Currency
		taxable_sales: DF.Currency
		zero_rated_sales: DF.Currency
	# end: auto-generated types

	pass
