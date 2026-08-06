import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry as erpnext_get_payment_entry,
)
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def fetch_wht_detail(item_code: str) -> dict:
	item = frappe.get_doc("Item", item_code)
	item.check_permission("read")

	if item.custom_thai_withholding_tax_income_type:
		return {
			"income_type": item.custom_thai_withholding_tax_income_type,
			"tax_rate": flt(item.custom_thai_withholding_tax_rate),
			"source": "Item",
		}

	group_values = frappe.db.get_value(
		"Item Group",
		item.item_group,
		["custom_thai_withholding_tax_income_type", "custom_thai_withholding_tax_rate"],
		as_dict=True,
	)
	if group_values and group_values.custom_thai_withholding_tax_income_type:
		return {
			"income_type": group_values.custom_thai_withholding_tax_income_type,
			"tax_rate": flt(group_values.custom_thai_withholding_tax_rate),
			"source": "Item Group",
		}

	return {"income_type": None, "tax_rate": 0, "source": None}


@frappe.whitelist()
def get_payment_entry(
	dt,
	dn,
	party_amount=None,
	bank_account=None,
	bank_amount=None,
	party_type=None,
	payment_type=None,
	reference_date=None,
	created_from_payment_request=False,
):
	payment_entry = erpnext_get_payment_entry(
		dt=dt,
		dn=dn,
		party_amount=party_amount,
		bank_account=bank_account,
		bank_amount=bank_amount,
		party_type=party_type,
		payment_type=payment_type,
		reference_date=reference_date,
		created_from_payment_request=created_from_payment_request,
	)

	if dt not in ("Sales Invoice", "Purchase Invoice"):
		return payment_entry

	invoice = frappe.get_doc(dt, dn)
	invoice.check_permission("read")
	if not invoice.get("is_return"):
		apply_thai_withholding_tax(payment_entry, invoice)

	return payment_entry


def apply_thai_withholding_tax(payment_entry, invoice):
	account_field = (
		"sales_withholding_tax_account"
		if invoice.doctype == "Sales Invoice"
		else "purchase_withholding_tax_account"
	)
	payment_ratio = get_payment_ratio(payment_entry, invoice)
	if not payment_ratio:
		return

	cost_center = payment_entry.cost_center or frappe.get_cached_value(
		"Company", payment_entry.company, "cost_center"
	)
	item_details = {}
	deductions = {}

	for item in invoice.get("items"):
		if not item.item_code:
			continue

		if item.item_code not in item_details:
			item_details[item.item_code] = fetch_wht_detail(item.item_code)
		detail = item_details[item.item_code]
		income_type = detail.get("income_type")
		rate = flt(detail.get("tax_rate"))
		if not income_type or not rate:
			continue

		tax_amount = flt(
			flt(item.base_net_amount) * payment_ratio * rate / 100,
			payment_entry.precision("amount", "deductions"),
		)
		if not tax_amount:
			continue

		account = frappe.get_cached_value("Thai Withholding Tax Income Type", income_type, account_field)
		if not account:
			frappe.throw(
				_("Please set {0} for Thai Withholding Tax Income Type {1}.").format(
					_(frappe.unscrub(account_field)), frappe.bold(income_type)
				)
			)

		key = (account, cost_center, income_type, rate)
		deductions[key] = flt(
			deductions.get(key, 0) + tax_amount,
			payment_entry.precision("amount", "deductions"),
		)

	if not deductions:
		return

	sign = 1 if invoice.doctype == "Sales Invoice" else -1
	for (account, row_cost_center, income_type, rate), amount in deductions.items():
		payment_entry.append(
			"deductions",
			{
				"account": account,
				"cost_center": row_cost_center,
				"amount": amount * sign,
				"description": _("Thai Withholding Tax: {0} ({1}%)").format(income_type, rate),
			},
		)

	total_tax = sum(deductions.values())
	payment_entry.paid_amount = flt(
		payment_entry.paid_amount - total_tax / (flt(payment_entry.source_exchange_rate) or 1),
		payment_entry.precision("paid_amount"),
	)
	payment_entry.received_amount = flt(
		payment_entry.received_amount - total_tax / (flt(payment_entry.target_exchange_rate) or 1),
		payment_entry.precision("received_amount"),
	)
	payment_entry.set_amounts()


def get_payment_ratio(payment_entry, invoice) -> float:
	party_account_currency = (
		payment_entry.paid_from_account_currency
		if payment_entry.payment_type == "Receive"
		else payment_entry.paid_to_account_currency
	)
	if party_account_currency == invoice.company_currency:
		invoice_total = invoice.get("base_rounded_total") or invoice.get("base_grand_total")
	else:
		invoice_total = invoice.get("rounded_total") or invoice.get("grand_total")

	allocated_amount = sum(
		abs(flt(reference.allocated_amount))
		for reference in payment_entry.get("references")
		if reference.reference_doctype == invoice.doctype and reference.reference_name == invoice.name
	)
	if not invoice_total or not allocated_amount:
		return 0

	return min(allocated_amount / abs(flt(invoice_total)), 1)
