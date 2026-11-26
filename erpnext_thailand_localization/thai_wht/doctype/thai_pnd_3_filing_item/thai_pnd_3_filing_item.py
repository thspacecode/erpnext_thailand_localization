# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ThaiPND3FilingItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_line1: DF.Data | None
		address_line2: DF.Data | None
		base_amount: DF.Currency
		country: DF.Link | None
		district: DF.Data | None
		income_description: DF.SmallText | None
		income_type: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_date: DF.Date
		postal_code: DF.Data | None
		province: DF.Data | None
		purchase_withholding_tax_entry: DF.Link
		recipient_branch_code: DF.Data
		recipient_first_name: DF.Data | None
		recipient_last_name: DF.Data | None
		recipient_name: DF.Data
		recipient_tax_id: DF.Data
		recipient_title: DF.Data | None
		reference_doc: DF.DynamicLink | None
		reference_doc_doctype: DF.Link | None
		reference_doc_item: DF.DynamicLink | None
		reference_doc_item_doctype: DF.Link | None
		subdistrict: DF.Data | None
		supplier: DF.Link
		supplier_address: DF.Link | None
		tax_amount: DF.Currency
		tax_payment_condition: DF.Literal[
			"Withheld", "Payer Bears Tax One Time", "Payer Bears Tax Continuously"
		]
		tax_rate: DF.Percent
		withholding_tax_entry_item: DF.Link
	# end: auto-generated types

	pass
