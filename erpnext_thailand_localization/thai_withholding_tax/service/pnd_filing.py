from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import add_days, add_months, get_first_day, getdate

from erpnext_thailand_localization.types import Json

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing_item.thai_pnd_3_filing_item import (
		ThaiPND3FilingItem,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing_item.thai_pnd_53_filing_item import (
		ThaiPND53FilingItem,
	)

	type EligibleFilingItem = ThaiPND3FilingItem | ThaiPND53FilingItem


def get_income_type_pnd(income_type: str | None, category: str | None) -> str | None:
	if not income_type or not category:
		return None
	return frappe.db.get_value(
		"Thai Withholding Tax Category Pnd",
		{
			"parent": income_type,
			"parenttype": "Thai Withholding Tax Income Type",
			"parentfield": "thai_withholding_tax_category_pnd",
			"thai_withholding_tax_category": category,
		},
		"pnd",
	)


@frappe.whitelist()
def get_eligible_items(
	return_doctype: str, company: str, tax_period: str
) -> list["Json[EligibleFilingItem]"]:
	form_types = {
		"Thai PND 3 Filing": "PND 3",
		"Thai PND 53 Filing": "PND 53",
	}
	if return_doctype not in form_types:
		frappe.throw(_("Unsupported PND filing type."))
	frappe.has_permission(return_doctype, "create", throw=True)

	period_start = get_first_day(getdate(tax_period))
	period_end = add_days(add_months(period_start, 1), -1)
	sources = frappe.get_all(
		"Purchase Withholding Tax Entry",
		filters={
			"company": company,
			"payment_date": ["between", [period_start, period_end]],
			"docstatus": 1,
		},
		pluck="name",
		order_by="payment_date, name",
	)

	filed_items = set()
	for item_doctype in ("Thai PND 3 Filing Item", "Thai PND 53 Filing Item"):
		filed_items.update(
			frappe.get_all(item_doctype, filters={"docstatus": 1}, pluck="withholding_tax_entry_item")
		)

	result = []
	for source_name in sources:
		source = frappe.get_doc("Purchase Withholding Tax Entry", source_name)
		category = frappe.get_cached_value(
			"Supplier", source.supplier, "custom_thai_withholding_tax_category"
		)
		for item in source.items:
			if item.name in filed_items:
				continue
			if get_income_type_pnd(item.income_type, category) != form_types[return_doctype]:
				continue
			result.append(
				{
					"purchase_withholding_tax_entry": source.name,
					"withholding_tax_entry_item": item.name,
					"payment_date": source.payment_date,
					"supplier": source.supplier,
					"supplier_address": source.supplier_address,
					"income_type": item.income_type,
					"base_amount": item.base_amount,
					"tax_rate": item.tax_rate,
					"tax_amount": item.tax_amount,
				}
			)
	return result
