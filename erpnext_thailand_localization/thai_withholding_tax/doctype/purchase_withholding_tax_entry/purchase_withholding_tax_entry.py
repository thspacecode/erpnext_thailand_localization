# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from erpnext_thailand_localization.thai_withholding_tax.model.withholding_tax_entry import (
	WithholdingTaxEntry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.payment_entry import (
	make_withholding_tax_entry,
)


class PurchaseWithholdingTaxEntry(WithholdingTaxEntry):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_thailand_localization.thai_withholding_tax.doctype.withholding_tax_entry_item.withholding_tax_entry_item import (
			WithholdingTaxEntryItem,
		)

		amended_from: DF.Link | None
		company: DF.Link
		company_currency: DF.Link
		items: DF.Table[WithholdingTaxEntryItem]
		naming_series: DF.Literal["PWHT-.YYYY.-.#####"]
		payment_date: DF.Date
		pnd: DF.Literal["PND 3", "PND 53"]
		supplier: DF.Link
		supplier_address: DF.Link
		total_base_amount: DF.Currency
		total_tax_amount: DF.Currency
	# end: auto-generated types

	party_type = "Supplier"
	party_field = "supplier"
	address_field = "supplier_address"
	payment_type = "Pay"

	def before_cancel(self) -> None:
		for item_doctype in ("Thai PND 3 Filing Item", "Thai PND 53 Filing Item"):
			if filed_return := frappe.db.get_value(
				item_doctype,
				{"purchase_withholding_tax_entry": self.name, "docstatus": 1},
				"parent",
			):
				frappe.throw(
					_("Cancel submitted PND filing {0} before cancelling this entry.").format(
						frappe.bold(filed_return)
					)
				)


@frappe.whitelist()
def make_purchase_withholding_tax_entry(
	source_name: str,
	target_doc: str | PurchaseWithholdingTaxEntry | None = None,
	kwargs: Mapping[str, Any] | None = None,
) -> PurchaseWithholdingTaxEntry:
	return make_withholding_tax_entry(
		source_name=source_name,
		target_doctype="Purchase Withholding Tax Entry",
		payment_type="Pay",
		party_type="Supplier",
		party_field="supplier",
		address_field="supplier_address",
		target_doc=target_doc,
	)
