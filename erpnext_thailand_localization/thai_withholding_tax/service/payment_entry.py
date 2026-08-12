import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	fetch_wht_detail,
	get_payment_ratio,
)


def make_withholding_tax_entry(
	source_name: str,
	target_doctype: str,
	payment_type: str,
	party_type: str,
	party_field: str,
	address_field: str,
	target_doc=None,
):
	source = frappe.get_doc("Payment Entry", source_name)
	source.check_permission("read")

	if source.docstatus != 1:
		frappe.throw(_("Payment Entry {0} must be submitted.").format(frappe.bold(source_name)))
	if source.payment_type != payment_type or source.party_type != party_type:
		frappe.throw(
			_("Payment Entry {0} is not eligible to create a {1}.").format(
				frappe.bold(source_name), _(target_doctype)
			)
		)
	if not frappe.has_permission(target_doctype, "create"):
		frappe.throw(
			_("You do not have permission to create a {0}.").format(_(target_doctype)), frappe.PermissionError
		)

	has_existing_target = bool(target_doc)
	party_doc = frappe.get_doc(party_type, source.party)
	party_doc.check_permission("read")

	invoice_doctype = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
	invoice_party_field = frappe.scrub(party_type)
	invoice_address_field = f"{invoice_party_field}_address"
	reference_invoices = []
	for reference in source.get("references") or []:
		if reference.reference_doctype != invoice_doctype:
			continue

		invoice = frappe.get_doc(invoice_doctype, reference.reference_name)
		invoice.check_permission("read")
		if invoice.company != source.company or invoice.get(invoice_party_field) != source.party:
			frappe.throw(
				_("Referenced {0} {1} does not belong to this Company and {2}.").format(
					_(invoice_doctype), frappe.bold(invoice.name), _(party_type)
				)
			)
		reference_invoices.append(invoice)

	invoice_addresses = [invoice.get(invoice_address_field) for invoice in reference_invoices]
	party_address = (
		invoice_addresses[0]
		if invoice_addresses and all(address == invoice_addresses[0] for address in invoice_addresses)
		else None
	)
	if not party_address:
		party_address = party_doc.get(f"{invoice_party_field}_primary_address")
	if party_address:
		frappe.get_doc("Address", party_address).check_permission("read")

	company_doc = frappe.get_doc("Company", source.company)
	company_doc.check_permission("read")
	company_currency = company_doc.default_currency

	def set_target_values(source_doc, target):
		values = {
			"company": source_doc.company,
			"company_currency": company_currency,
			"payment_date": source_doc.posting_date,
			party_field: source_doc.party,
			address_field: party_address,
		}
		for fieldname, value in values.items():
			if not has_existing_target or not target.get(fieldname):
				target.set(fieldname, value)

		item_details = {}
		for invoice in reference_invoices:
			payment_ratio = get_payment_ratio(source_doc, invoice)
			if not payment_ratio:
				continue

			for invoice_item in invoice.get("items") or []:
				if not invoice_item.item_code:
					continue
				if invoice_item.item_code not in item_details:
					item_details[invoice_item.item_code] = fetch_wht_detail(
						invoice_item.item_code,
						party_type=party_type,
						party=source_doc.party,
						company=source_doc.company,
					)

				detail = item_details[invoice_item.item_code]
				base_amount = flt(
					flt(invoice_item.base_net_amount) * payment_ratio,
					target.precision("base_amount", "items"),
				)
				tax_rate = flt(detail.get("tax_rate"))
				if not detail.get("income_type") or not base_amount or not tax_rate:
					continue

				target.append(
					"items",
					{
						"income_type": detail.get("income_type"),
						"base_amount": base_amount,
						"tax_rate": tax_rate,
						"reference_doc_doctype": invoice.doctype,
						"reference_doc": invoice.name,
						"reference_doc_item_doctype": invoice_item.doctype,
						"reference_doc_item": invoice_item.name,
					},
				)

		target.calculate_totals()

	return get_mapped_doc(
		"Payment Entry",
		source_name,
		{
			"Payment Entry": {
				"doctype": target_doctype,
				"field_no_map": ["naming_series", "company", "company_currency"],
			}
		},
		target_doc,
		set_target_values,
	)
