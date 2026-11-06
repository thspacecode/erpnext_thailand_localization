from typing import TypedDict

import frappe


class UndueValueAddedTaxDetail(TypedDict):
	allow_sales: bool
	allow_purchase: bool


@frappe.whitelist()
def fetch_undue_vat_detail(item_code: str) -> UndueValueAddedTaxDetail:
	"""Resolve each allowance from the Item, then its direct Item Group."""
	item = frappe.get_doc("Item", item_code)
	item.check_permission("read")
	item_group = frappe.get_cached_doc("Item Group", item.item_group)
	return {
		"allow_sales": (
			item.get("custom_allow_undue_sales_value_added_tax")
			or item_group.get("custom_allow_undue_sales_value_added_tax")
		)
		== "Allow",
		"allow_purchase": (
			item.get("custom_allow_undue_purchase_value_added_tax")
			or item_group.get("custom_allow_undue_purchase_value_added_tax")
		)
		== "Allow",
	}
