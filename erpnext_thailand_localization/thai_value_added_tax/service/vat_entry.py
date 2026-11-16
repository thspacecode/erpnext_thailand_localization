"""Create reviewed-later register entries from explicit recognized THB amounts."""

import hashlib
import json
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _


def generation_key(source_type, source_name, identity):
	return hashlib.sha256(json.dumps([source_type, source_name, identity]).encode()).hexdigest()


def money(value):
	try:
		amount = Decimal(str(value or 0))
		if not amount.is_finite():
			raise InvalidOperation
		return amount
	except (InvalidOperation, ValueError):
		frappe.throw(_("VAT amounts must be finite numbers."))


def group_rows(rows):
	"""Keep tax invoices, establishments, categories and declared rates separate."""
	groups = {}
	seen = set()
	for value in rows:
		row = frappe._dict(value)
		if not row.source_identity or row.source_identity in seen:
			frappe.throw(_("VAT source row identity must be present and unique."))
		seen.add(row.source_identity)
		if row.vat_category not in ("Taxable", "Zero Rated", "Exempt"):
			frappe.throw(_("Select an explicit VAT category."))
		base, tax = money(row.tax_base), money(row.tax_amount)
		if not base or base * tax < 0:
			frappe.throw(_("VAT base must be nonzero and have the same sign as VAT."))
		if row.vat_category != "Taxable" and tax:
			frappe.throw(_("Zero-rated and exempt entries must have zero VAT."))
		key = tuple(
			row.get(field)
			for field in (
				"direction",
				"party",
				"party_name",
				"tax_id",
				"branch_code",
				"company_tax_address",
				"tax_invoice_number",
				"tax_invoice_identity",
				"tax_invoice_date",
				"tax_invoice_book",
				"report_date",
				"vat_category",
				"rate",
			)
		)
		if key not in groups:
			groups[key] = row.copy()
			groups[key].update(tax_base=Decimal(0), tax_amount=Decimal(0), identities=[])
		group = groups[key]
		group.tax_base += base
		group.tax_amount += tax
		group.identities.append(row.source_identity)
	return list(groups.values())


def create_entries(source, rows):
	"""Run in the caller transaction. Never update an existing generated entry."""
	if source.docstatus != 1:
		frappe.throw(_("VAT source must be submitted."))
	source.check_permission("read")
	frappe.get_doc(source.doctype, source.name, for_update=True)
	company = frappe.get_cached_doc("Company", source.company)
	if company.default_currency != "THB":
		frappe.throw(_("VAT reporting requires Company currency THB."))
	entries = []
	for row in group_rows(rows):
		if row.direction not in ("Sales", "Purchase"):
			frappe.throw(_("Select a VAT direction."))
		if source.doctype in ("Sales Invoice", "Purchase Invoice"):
			expected = "Sales" if source.doctype == "Sales Invoice" else "Purchase"
			party = source.get("customer" if expected == "Sales" else "supplier")
			if row.direction != expected or row.party != party:
				frappe.throw(_("VAT direction and party must match the source invoice."))
		if source.doctype in ("Journal Entry", "Expense Claim") and (
			not row.tax_invoice_number or not row.tax_invoice_date
		):
			frappe.throw(_("Explicit tax invoice number and date are required for this source."))
		doctype = f"{row.direction} VAT Entry"
		identity = hashlib.sha256(json.dumps(sorted(row.identities)).encode()).hexdigest()
		key = generation_key(source.doctype, source.name, identity)
		existing = frappe.db.get_value(doctype, {"generation_key": key}, "name")
		if existing:
			entries.append(frappe.get_doc(doctype, existing))
			continue
		entry = frappe.new_doc(doctype)
		for field in (
			"party",
			"party_name",
			"tax_id",
			"branch_code",
			"company_tax_address",
			"tax_invoice_number",
			"tax_invoice_date",
			"tax_invoice_book",
			"report_date",
			"vat_category",
			"tax_base",
			"tax_amount",
		):
			entry.set(field, row.get(field))
		entry.update(
			dict(
				company=source.company,
				account=company.get(f"{row.direction.lower()}_value_added_tax_account"),
				voucher_type=source.doctype,
				voucher_no=source.name,
				source_identity=identity,
				generation_key=key,
			)
		)
		entry.insert()
		entries.append(entry)
	return entries


def find_entries(source):
	entries = []
	for doctype in ("Purchase VAT Entry", "Sales VAT Entry"):
		for name in frappe.get_all(
			doctype,
			filters={
				"voucher_type": source.doctype,
				"voucher_no": source.name,
				"generation_key": ["is", "set"],
				"docstatus": ["!=", 2],
			},
			pluck="name",
			order_by="name",
		):
			entries.append(frappe.get_doc(doctype, name, for_update=True))
	return entries


def cancel_entries(source):
	"""Check all PP30 locks before changing any register entry."""
	entries = find_entries(source)
	for entry in entries:
		entry.before_cancel()
	for entry in entries:
		if entry.docstatus == 1:
			entry.cancel()
		else:
			# Draft documents cannot use Document.cancel; retain the generation tombstone.
			entry.db_set("docstatus", 2, update_modified=True)
