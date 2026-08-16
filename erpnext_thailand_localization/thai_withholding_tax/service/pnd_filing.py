from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import add_days, add_months, get_first_day, getdate

from erpnext_thailand_localization.types import Json

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing.thai_pnd_3_filing import (
		ThaiPND3Filing,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing_item.thai_pnd_3_filing_item import (
		ThaiPND3FilingItem,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing.thai_pnd_53_filing import (
		ThaiPND53Filing,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing_item.thai_pnd_53_filing_item import (
		ThaiPND53FilingItem,
	)

	type EligibleFilingItem = ThaiPND3FilingItem | ThaiPND53FilingItem
	type Filing = ThaiPND3Filing | ThaiPND53Filing


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


def get_filing_pnd_type(return_doctype: str) -> str:
	form_types = {
		"Thai PND 3 Filing": "PND 3",
		"Thai PND 53 Filing": "PND 53",
	}
	if return_doctype not in form_types:
		frappe.throw(_("Unsupported PND filing type."))
	return form_types[return_doctype]


@frappe.whitelist()
def get_eligible_items(
	return_doctype: str,
	company: str,
	tax_period: str,
	source_names: list[str] | None = None,
) -> list["Json[EligibleFilingItem]"]:
	pnd_type = get_filing_pnd_type(return_doctype)
	frappe.has_permission(return_doctype, "create", throw=True)

	period_start = get_first_day(getdate(tax_period))
	period_end = add_days(add_months(period_start, 1), -1)
	source_filters = {
		"company": company,
		"payment_date": ["between", [period_start, period_end]],
		"pnd": pnd_type,
		"docstatus": 1,
	}
	if source_names is not None:
		source_filters["name"] = ["in", source_names]

	sources = frappe.get_all(
		"Purchase Withholding Tax Entry",
		filters=source_filters,
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
		for item in source.items:
			if item.name in filed_items:
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_unfiled_purchase_withholding_tax_entries(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict[str, object],
	as_dict: bool = False,
) -> list[object]:
	if doctype != "Purchase Withholding Tax Entry":
		frappe.throw(_("Only Purchase Withholding Tax Entry documents are supported."))

	query_filters = dict(filters)
	return_doctype = str(query_filters.pop("return_doctype", ""))
	tax_period = str(query_filters.pop("tax_period", ""))
	company = str(query_filters.get("company", ""))
	payment_date = query_filters.get("payment_date")
	if isinstance(payment_date, list) and len(payment_date) == 2 and payment_date[0] != "between":
		query_filters["payment_date"] = ["between", payment_date]

	eligible_items = get_eligible_items(return_doctype, company, tax_period)
	eligible_sources = {item["purchase_withholding_tax_entry"] for item in eligible_items}
	if not eligible_sources:
		return []

	query_filters["docstatus"] = 1
	purchase_withholding_tax_entry = frappe.qb.DocType("Purchase Withholding Tax Entry")
	query = frappe.qb.get_query(
		"Purchase Withholding Tax Entry",
		fields=["name", "company", "payment_date", "supplier"],
		filters=query_filters,
		ignore_permissions=False,
	)
	query = (
		query.where(
			purchase_withholding_tax_entry.name.isin(eligible_sources)
			& purchase_withholding_tax_entry[searchfield].like(f"%{txt}%")
		)
		.orderby(purchase_withholding_tax_entry.payment_date)
		.orderby(purchase_withholding_tax_entry.name)
		.limit(page_len)
		.offset(start)
	)
	return query.run(as_dict=as_dict)


@frappe.whitelist()
def add_purchase_withholding_tax_entry_to_filing(
	source_name: str,
	target_doc: "str | Filing",
) -> "Filing":
	if isinstance(target_doc, str):
		target_doc = frappe.get_doc(frappe.parse_json(target_doc))

	get_filing_pnd_type(target_doc.doctype)
	target_doc.check_permission("create" if target_doc.is_new() else "write")
	if target_doc.docstatus != 0:
		frappe.throw(_("Purchase Withholding Tax Entries can only be added to a draft filing."))
	if not target_doc.company or not target_doc.tax_period:
		frappe.throw(_("Please set Company and Tax Period first."))

	source = frappe.get_doc("Purchase Withholding Tax Entry", source_name)
	source.check_permission("read")
	eligible_items = get_eligible_items(
		target_doc.doctype,
		target_doc.company,
		target_doc.tax_period,
		source_names=[source_name],
	)
	existing_items = {item.withholding_tax_entry_item for item in target_doc.items}
	eligible_items = [
		item for item in eligible_items if item["withholding_tax_entry_item"] not in existing_items
	]
	if not eligible_items:
		frappe.throw(
			_("Purchase Withholding Tax Entry {0} has no unfiled items eligible for this filing.").format(
				frappe.bold(source_name)
			)
		)

	for item in eligible_items:
		target_doc.append("items", item)
	target_doc.run_method("set_item_snapshots")
	target_doc.run_method("calculate_totals")
	return target_doc
