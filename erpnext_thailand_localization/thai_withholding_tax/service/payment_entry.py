from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing import (
	get_income_type_pnd,
)
from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	get_reference_withholding_tax_deductions,
)
from erpnext_thailand_localization.types import Json

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.payment_entry_deduction.payment_entry_deduction import (
		PaymentEntryDeduction,
	)

	from erpnext_thailand_localization.thai_withholding_tax.model.withholding_tax_entry import (
		WithholdingTaxEntry,
	)


@frappe.whitelist()
def get_withholding_tax_from_references(
	doc: "str | Json[PaymentEntry]",
) -> list["Json[PaymentEntryDeduction]"]:
	payment_entry = frappe.get_doc(frappe.parse_json(doc))
	if payment_entry.doctype != "Payment Entry":
		frappe.throw(_("Only Payment Entry documents are supported."))
	if payment_entry.docstatus != 0:
		frappe.throw(_("Withholding tax can only be fetched for a draft Payment Entry."))
	if payment_entry.payment_type not in ("Pay", "Receive"):
		frappe.throw(_("Withholding tax is not supported for Internal Transfer."))

	expected_party_type = "Customer" if payment_entry.payment_type == "Receive" else "Supplier"
	if payment_entry.party_type != expected_party_type or not payment_entry.party:
		frappe.throw(
			_("Payment Type {0} requires Party Type {1} to fetch withholding tax.").format(
				_(payment_entry.payment_type), _(expected_party_type)
			)
		)
	if not payment_entry.has_permission("write"):
		frappe.throw(_("You do not have permission to edit this Payment Entry."), frappe.PermissionError)

	reference_doctypes = (
		("Sales Invoice", "Sales Order")
		if payment_entry.payment_type == "Receive"
		else ("Purchase Invoice", "Purchase Order")
	)
	deductions = []
	seen_references = set()
	for reference in payment_entry.get("references") or []:
		key = (reference.reference_doctype, reference.reference_name)
		if (
			reference.reference_doctype not in reference_doctypes
			or not reference.reference_name
			or not flt(reference.allocated_amount)
			or key in seen_references
		):
			continue
		seen_references.add(key)

		reference_document = frappe.get_doc(*key)
		reference_document.check_permission("read")
		if (
			reference_document.company != payment_entry.company
			or reference_document.get(frappe.scrub(payment_entry.party_type)) != payment_entry.party
		):
			frappe.throw(
				_("Referenced {0} {1} does not belong to this Company and Party.").format(
					_(reference_document.doctype), frappe.bold(reference_document.name)
				)
			)
		deductions.extend(get_reference_withholding_tax_deductions(payment_entry, reference_document))

	return deductions


@frappe.whitelist()
def has_existing_withholding_tax_entry(payment_entry: str) -> bool:
	document = frappe.get_doc("Payment Entry", payment_entry)
	document.check_permission("read")

	return bool(
		frappe.db.exists(
			"Withholding Tax Entry Item",
			{
				"reference_doc_doctype": "Payment Entry",
				"reference_doc": payment_entry,
				"parenttype": [
					"in",
					["Sales Withholding Tax Entry", "Purchase Withholding Tax Entry"],
				],
				"docstatus": ["<", 2],
			},
		)
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payment_entries_with_pending_withholding_tax(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict,
	as_dict: bool = False,
) -> list[object]:
	if doctype != "Payment Entry":
		frappe.throw(_("Only Payment Entry documents are supported."))

	payment_type = filters.get("payment_type")
	party_type = filters.get("party_type")
	if (payment_type, party_type) not in (("Receive", "Customer"), ("Pay", "Supplier")):
		frappe.throw(_("Payment Type and Party Type are not eligible for withholding tax."))

	payment_entry = frappe.qb.DocType("Payment Entry")
	deduction = frappe.qb.DocType("Payment Entry Deduction")
	entry_item = frappe.qb.DocType("Withholding Tax Entry Item")

	claimed_deductions = (
		frappe.qb.from_(entry_item)
		.select(entry_item.reference_doc_item)
		.where(
			(entry_item.reference_doc_item_doctype == "Payment Entry Deduction")
			& entry_item.parenttype.isin(["Sales Withholding Tax Entry", "Purchase Withholding Tax Entry"])
			& (entry_item.docstatus < 2)
			& entry_item.reference_doc_item.isnotnull()
		)
	)
	pending_payment_entries = (
		frappe.qb.from_(deduction)
		.select(deduction.parent)
		.where(
			(deduction.parenttype == "Payment Entry")
			& (deduction.parentfield == "deductions")
			& (deduction.custom_is_withholding_tax_entry == 1)
			& deduction.custom_income_type.isnotnull()
			& (deduction.custom_income_type != "")
			& (deduction.custom_base_amount > 0)
			& (deduction.custom_tax_rate > 0)
			& deduction.name.notin(claimed_deductions)
		)
	)

	query = frappe.qb.get_query(
		"Payment Entry",
		fields=["name", "company", "party", "posting_date"],
		filters=filters,
		ignore_permissions=False,
	)
	query = (
		query.where(
			(payment_entry.docstatus == 1)
			& (payment_entry.payment_type == payment_type)
			& (payment_entry.party_type == party_type)
			& payment_entry.name.isin(pending_payment_entries)
			& payment_entry[searchfield].like(f"%{txt}%")
		)
		.orderby(payment_entry[searchfield])
		.limit(page_len)
		.offset(start)
	)
	return query.run(as_dict=as_dict)


def map_payment_entry_deductions(
	payment_entry: "PaymentEntry", withholding_tax_entry: "WithholdingTaxEntry"
) -> None:
	existing_deductions = {
		item.reference_doc_item
		for item in withholding_tax_entry.get("items") or []
		if item.reference_doc_item_doctype == "Payment Entry Deduction"
	}
	eligible_deductions = [
		deduction
		for deduction in payment_entry.get("deductions") or []
		if deduction.custom_is_withholding_tax_entry
		and deduction.custom_income_type
		and flt(deduction.custom_base_amount) > 0
		and flt(deduction.custom_tax_rate) > 0
		and deduction.name not in existing_deductions
	]
	claimed_rows = (
		frappe.get_all(
			"Withholding Tax Entry Item",
			filters={
				"reference_doc_item_doctype": "Payment Entry Deduction",
				"reference_doc_item": ["in", [deduction.name for deduction in eligible_deductions]],
				"parenttype": [
					"in",
					["Sales Withholding Tax Entry", "Purchase Withholding Tax Entry"],
				],
				"docstatus": ["<", 2],
			},
			fields=["reference_doc_item", "parent", "parenttype"],
		)
		if eligible_deductions
		else []
	)
	claimed_deductions = {
		row.reference_doc_item
		for row in claimed_rows
		if row.parent != withholding_tax_entry.name or row.parenttype != withholding_tax_entry.doctype
	}

	for deduction in eligible_deductions:
		if deduction.name in claimed_deductions:
			continue

		withholding_tax_entry.append(
			"items",
			{
				"income_type": deduction.custom_income_type,
				"base_amount": deduction.custom_base_amount,
				"tax_rate": deduction.custom_tax_rate,
				"reference_doc_doctype": "Payment Entry",
				"reference_doc": payment_entry.name,
				"reference_doc_item_doctype": "Payment Entry Deduction",
				"reference_doc_item": deduction.name,
			},
		)
		existing_deductions.add(deduction.name)


def make_withholding_tax_entry(
	source_name: str,
	target_doctype: str,
	payment_type: str,
	party_type: str,
	party_field: str,
	address_field: str,
	target_doc: "str | WithholdingTaxEntry | None" = None,
) -> "WithholdingTaxEntry":
	# Load the source Payment Entry and verify that the user can access it.
	source = frappe.get_doc("Payment Entry", source_name)
	source.check_permission("read")

	# Validate that the Payment Entry can create the requested withholding tax entry.
	if source.docstatus != 1:
		frappe.throw(_("Payment Entry {0} must be submitted.").format(frappe.bold(source_name)))
	if source.payment_type != payment_type or source.party_type != party_type:
		frappe.throw(
			_("Payment Entry {0} is not eligible to create a {1}.").format(
				frappe.bold(source_name), _(target_doctype)
			)
		)
	if not source.party:
		frappe.throw(_("Payment Entry {0} must have a Party.").format(frappe.bold(source_name)))
	if not frappe.has_permission(target_doctype, "create"):
		frappe.throw(
			_("You do not have permission to create a {0}.").format(_(target_doctype)), frappe.PermissionError
		)

	# Track whether values should be preserved while appending to an existing target.
	has_existing_target = bool(target_doc)

	# Resolve the party's primary or first linked address and check access to it.
	party_doc = frappe.get_doc(party_type, source.party)
	party_doc.check_permission("read")
	party_reference_field = frappe.scrub(party_type)
	party_address = party_doc.get(f"{party_reference_field}_primary_address")
	if not party_address:
		party_address = frappe.db.get_value(
			"Dynamic Link",
			{
				"link_doctype": party_type,
				"link_name": source.party,
				"parenttype": "Address",
			},
			"parent",
			order_by="idx, creation",
		)
	if party_address:
		frappe.get_doc("Address", party_address).check_permission("read")

	# Load the company currency used to calculate the target entry totals.
	company_doc = frappe.get_doc("Company", source.company)
	company_doc.check_permission("read")
	company_currency = company_doc.default_currency

	# Populate and validate values that are not handled by the document mapper.
	def set_target_values(source_doc: "PaymentEntry", target: "WithholdingTaxEntry") -> None:
		# Ensure an existing target belongs to the same company and party.
		if has_existing_target:
			if target.company and target.company != source_doc.company:
				frappe.throw(
					_("Payment Entry {0} does not belong to Company {1}.").format(
						frappe.bold(source_doc.name), frappe.bold(target.company)
					)
				)
			if target.get(party_field) and target.get(party_field) != source_doc.party:
				frappe.throw(
					_("Payment Entry {0} does not belong to {1} {2}.").format(
						frappe.bold(source_doc.name), _(party_type), frappe.bold(target.get(party_field))
					)
				)

		# Set mapped header values without overwriting values already on an existing target.
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

		# Add eligible deductions and refresh the withholding tax totals.
		map_payment_entry_deductions(source_doc, target)
		if target_doctype == "Purchase Withholding Tax Entry":
			category = frappe.get_cached_value(
				party_type, source_doc.party, "custom_thai_withholding_tax_category"
			)
			pnd_types = {
				pnd for item in target.items if (pnd := get_income_type_pnd(item.income_type, category))
			}
			target.pnd = pnd_types.pop() if len(pnd_types) == 1 else None
		target.calculate_totals()

	# Map the Payment Entry and apply the target-specific post-processing above.
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
