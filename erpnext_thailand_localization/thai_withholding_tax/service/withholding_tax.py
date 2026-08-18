from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, TypedDict

import frappe
from frappe import _
from frappe.utils import flt

from erpnext_thailand_localization.types import Json

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.payment_entry_deduction.payment_entry_deduction import (
		PaymentEntryDeduction,
	)
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
	from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_withholding_tax_rate_by_category.thai_withholding_tax_rate_by_category import (
		ThaiWithholdingTaxRateByCategory,
	)

	type ReferenceDocument = SalesInvoice | SalesOrder | PurchaseInvoice | PurchaseOrder


class WithholdingTaxDetail(TypedDict):
	income_type: str | None
	tax_rate: float
	source: Literal["Item", "Item Group"] | None


@frappe.whitelist()
def fetch_wht_detail(
	item_code: str,
	party_type: str | None = None,
	party: str | None = None,
	company: str | None = None,
) -> WithholdingTaxDetail:
	item = frappe.get_doc("Item", item_code)
	item.check_permission("read")
	category = get_thai_withholding_tax_category(party_type, party, company)

	if item.custom_thai_withholding_tax_income_type:
		return {
			"income_type": item.custom_thai_withholding_tax_income_type,
			"tax_rate": get_wht_rate(
				item.custom_thai_withholding_tax_income_type,
				item.custom_thai_withholding_tax_rate,
				item.get("custom_thai_withholding_tax_rate_by_category"),
				category,
			),
			"source": "Item",
		}

	item_group = frappe.get_cached_doc("Item Group", item.item_group)
	if item_group.custom_thai_withholding_tax_income_type:
		return {
			"income_type": item_group.custom_thai_withholding_tax_income_type,
			"tax_rate": get_wht_rate(
				item_group.custom_thai_withholding_tax_income_type,
				item_group.custom_thai_withholding_tax_rate,
				item_group.get("custom_thai_withholding_tax_rate_by_category"),
				category,
			),
			"source": "Item Group",
		}

	return {"income_type": None, "tax_rate": 0, "source": None}


def get_thai_withholding_tax_category(
	party_type: str | None,
	party: str | None,
	company: str | None,
) -> str | None:
	if party_type == "Supplier":
		if party:
			return frappe.get_cached_value("Supplier", party, "custom_thai_withholding_tax_category")
		return None

	if company:
		return frappe.get_cached_value("Company", company, "custom_thai_withholding_tax_category")

	return None


def get_wht_rate(
	income_type: str,
	configured_rate: str | float | None,
	configured_rates_by_category: Sequence["ThaiWithholdingTaxRateByCategory"] | None = None,
	category: str | None = None,
) -> float:
	category_rate = get_rate_by_category(configured_rates_by_category, category)
	if category_rate is not None:
		return category_rate

	default_rate = parse_rate(configured_rate)
	if default_rate is not None:
		return default_rate

	income_type_doc = frappe.get_cached_doc("Thai Withholding Tax Income Type", income_type)
	category_rate = get_rate_by_category(
		income_type_doc.get("thai_withholding_tax_rate_by_category"), category
	)
	if category_rate is not None:
		return category_rate

	default_rate = parse_rate(income_type_doc.default_thai_withholding_tax_rate)
	return default_rate if default_rate is not None else 0


def parse_rate(rate: str | float | None) -> float | None:
	if rate is None or not str(rate).strip():
		return None

	return flt(rate)


def get_rate_by_category(
	rates_by_category: Sequence["ThaiWithholdingTaxRateByCategory"] | None,
	category: str | None,
) -> float | None:
	if not category:
		return None

	for row in rates_by_category or []:
		if row.thai_withholding_tax_category == category:
			return parse_rate(row.rate)

	return None


def is_withholding_tax_enabled(
	company: str,
	withholding_tax_type: Literal["Sales", "Purchase"],
) -> bool:
	fieldname = f"enable_{frappe.scrub(withholding_tax_type)}_withholding_tax"
	return bool(frappe.get_cached_value("Company", company, fieldname))


def get_reference_withholding_tax_deductions(
	payment_entry: "PaymentEntry",
	reference_document: "ReferenceDocument",
) -> list[Json["PaymentEntryDeduction"]]:
	withholding_tax_type = (
		"Sales" if reference_document.doctype in ("Sales Invoice", "Sales Order") else "Purchase"
	)
	if not is_withholding_tax_enabled(payment_entry.company, withholding_tax_type):
		return []

	payment_ratio = get_payment_ratio(payment_entry, reference_document)
	if not payment_ratio:
		return []

	cost_center = payment_entry.cost_center or frappe.get_cached_value(
		"Company", payment_entry.company, "cost_center"
	)
	party_type = "Customer" if reference_document.doctype in ("Sales Invoice", "Sales Order") else "Supplier"
	party = reference_document.get(frappe.scrub(party_type))
	category = get_thai_withholding_tax_category(party_type, party, payment_entry.company)
	item_details = {}
	deductions = []
	sign = 1 if reference_document.doctype in ("Sales Invoice", "Sales Order") else -1

	for item in reference_document.get("items") or []:
		if not item.item_code:
			continue

		if item.item_code not in item_details:
			item_details[item.item_code] = fetch_wht_detail(
				item.item_code,
				party_type=party_type,
				party=party,
				company=payment_entry.company,
			)
		detail = item_details[item.item_code]
		income_type = detail.get("income_type")
		rate = flt(detail.get("tax_rate"))
		base_amount = flt(
			flt(item.base_net_amount) * payment_ratio,
			payment_entry.precision("amount", "deductions"),
		)
		if not income_type or rate <= 0 or not base_amount:
			continue

		tax_amount = flt(
			base_amount * rate / 100,
			payment_entry.precision("amount", "deductions"),
		)
		if not tax_amount:
			continue

		deductions.append(
			{
				"account": get_withholding_tax_account(
					payment_entry.company,
					reference_document.doctype,
					income_type,
					category,
				),
				"cost_center": cost_center,
				"amount": tax_amount * sign,
				"description": _("Thai Withholding Tax: {0} ({1}%)").format(income_type, rate),
				"custom_is_withholding_tax_entry": 1,
				"custom_income_type": income_type,
				"custom_tax_rate": rate,
				"custom_base_amount": base_amount,
				"custom_reference_document_type": reference_document.doctype,
				"custom_reference_document": reference_document.name,
				"custom_reference_item_type": item.doctype,
				"custom_reference_item": item.name,
				"custom_item_code": item.item_code,
			}
		)

	return deductions


def apply_thai_withholding_tax(
	payment_entry: "PaymentEntry",
	reference_document: "ReferenceDocument",
) -> None:
	deductions = get_reference_withholding_tax_deductions(payment_entry, reference_document)
	if not deductions:
		return

	for deduction in deductions:
		payment_entry.append("deductions", deduction)

	total_tax = sum(abs(flt(deduction["amount"])) for deduction in deductions)
	payment_entry.paid_amount = flt(
		payment_entry.paid_amount - total_tax / (flt(payment_entry.source_exchange_rate) or 1),
		payment_entry.precision("paid_amount"),
	)
	payment_entry.received_amount = flt(
		payment_entry.received_amount - total_tax / (flt(payment_entry.target_exchange_rate) or 1),
		payment_entry.precision("received_amount"),
	)
	payment_entry.set_amounts()


def get_withholding_tax_account(
	company: str,
	reference_doctype: str,
	income_type: str,
	category: str | None,
) -> str:
	if reference_doctype in ("Sales Invoice", "Sales Order"):
		account_field = "sales_withholding_tax_account"
	else:
		if not category:
			frappe.throw(
				_("Please set Thai Withholding Tax Category for the supplier."),
			)

		pnd = frappe.db.get_value(
			"Thai Withholding Tax Category Pnd",
			{
				"parent": income_type,
				"parenttype": "Thai Withholding Tax Income Type",
				"parentfield": "thai_withholding_tax_category_pnd",
				"thai_withholding_tax_category": category,
			},
			"pnd",
		)
		if not pnd:
			frappe.throw(
				_("Please set PND for Thai Withholding Tax Category {0} on Income Type {1}.").format(
					frappe.bold(category), frappe.bold(income_type)
				)
			)

		account_field = {
			"PND 3": "purchase_withholding_tax_pnd3_account",
			"PND 53": "purchase_withholding_tax_pnd53_account",
		}.get(pnd)
		if not account_field:
			frappe.throw(
				_("Purchase withholding tax account is not supported for {0}.").format(frappe.bold(pnd))
			)

	account = frappe.get_cached_value("Company", company, account_field)
	if not account:
		frappe.throw(
			_("Please set {0} for Company {1}.").format(
				_(frappe.unscrub(account_field)), frappe.bold(company)
			)
		)

	return account


def get_payment_ratio(
	payment_entry: "PaymentEntry",
	reference_document: "ReferenceDocument",
) -> float:
	party_account_currency = (
		payment_entry.paid_from_account_currency
		if payment_entry.payment_type == "Receive"
		else payment_entry.paid_to_account_currency
	)
	if party_account_currency == reference_document.company_currency:
		reference_total = reference_document.get("base_rounded_total") or reference_document.get(
			"base_grand_total"
		)
	else:
		reference_total = reference_document.get("rounded_total") or reference_document.get("grand_total")

	allocated_amount = sum(
		abs(flt(reference.allocated_amount))
		for reference in payment_entry.get("references")
		if reference.reference_doctype == reference_document.doctype
		and reference.reference_name == reference_document.name
	)
	if not reference_total or not allocated_amount:
		return 0

	return min(allocated_amount / abs(flt(reference_total)), 1)
