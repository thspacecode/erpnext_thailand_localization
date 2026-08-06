# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext_thailand_localization.thai_withholding_tax.payment_entry import make_withholding_tax_entry
from erpnext_thailand_localization.thai_withholding_tax.withholding_tax_entry import WithholdingTaxEntry


class PurchaseWithholdingTaxEntry(WithholdingTaxEntry):
	party_type = "Supplier"
	party_field = "supplier"
	address_field = "supplier_address"


@frappe.whitelist()
def make_purchase_withholding_tax_entry(source_name, target_doc=None, kwargs=None):
	return make_withholding_tax_entry(
		source_name=source_name,
		target_doctype="Purchase Withholding Tax Entry",
		payment_type="Pay",
		party_type="Supplier",
		party_field="supplier",
		address_field="supplier_address",
		target_doc=target_doc,
	)
