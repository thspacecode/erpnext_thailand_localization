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

	reference_doctypes = (
		("Sales Invoice", "Sales Order")
		if party_type == "Customer"
		else ("Purchase Invoice", "Purchase Order")
	)
	party_reference_field = frappe.scrub(party_type)
	party_address_field = f"{party_reference_field}_address"
	reference_documents = []
	for reference in source.get("references") or []:
		if reference.reference_doctype not in reference_doctypes:
			continue

		reference_document = frappe.get_doc(reference.reference_doctype, reference.reference_name)
		reference_document.check_permission("read")
		if (
			reference_document.company != source.company
			or reference_document.get(party_reference_field) != source.party
		):
			frappe.throw(
				_("Referenced {0} {1} does not belong to this Company and {2}.").format(
					_(reference_document.doctype), frappe.bold(reference_document.name), _(party_type)
				)
			)
		reference_documents.append(reference_document)

	reference_addresses = [
		reference_document.get(party_address_field) for reference_document in reference_documents
	]
	party_address = (
		reference_addresses[0]
		if reference_addresses and all(address == reference_addresses[0] for address in reference_addresses)
		else None
	)
	if not party_address:
		party_address = party_doc.get(f"{party_reference_field}_primary_address")
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
		for reference_document in reference_documents:
			payment_ratio = get_payment_ratio(source_doc, reference_document)
			if not payment_ratio:
				continue

			for reference_item in reference_document.get("items") or []:
				if not reference_item.item_code:
					continue
				if reference_item.item_code not in item_details:
					item_details[reference_item.item_code] = fetch_wht_detail(
						reference_item.item_code,
						party_type=party_type,
						party=source_doc.party,
						company=source_doc.company,
					)

				detail = item_details[reference_item.item_code]
				base_amount = flt(
					flt(reference_item.base_net_amount) * payment_ratio,
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
						"reference_doc_doctype": reference_document.doctype,
						"reference_doc": reference_document.name,
						"reference_doc_item_doctype": reference_item.doctype,
						"reference_doc_item": reference_item.name,
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
