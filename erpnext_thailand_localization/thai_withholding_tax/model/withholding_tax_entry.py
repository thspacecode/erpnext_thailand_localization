from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.withholding_tax_entry_item.withholding_tax_entry_item import (
		WithholdingTaxEntryItem,
	)


class WithholdingTaxEntry(Document):
	party_type: str
	party_field: str
	address_field: str
	payment_type: str

	def validate(self) -> None:
		self.validate_payment_entry_deductions()
		self.calculate_totals()

	def before_submit(self) -> None:
		self.validate_party_address()
		for item in self.items:
			row_label = _("Row {0}").format(item.idx)
			self.validate_item(item, row_label)
			self.validate_reference(item, row_label)

	def validate_payment_entry_deductions(self) -> None:
		payment_entry_rows = []
		seen_deductions = set()
		for item in self.items:
			is_payment_entry_reference = item.reference_doc_doctype == "Payment Entry"
			is_deduction_reference = item.reference_doc_item_doctype == "Payment Entry Deduction"
			if not is_payment_entry_reference and not is_deduction_reference:
				continue

			row_label = _("Row {0}").format(item.idx)
			if (
				not is_payment_entry_reference
				or not is_deduction_reference
				or not item.reference_doc
				or not item.reference_doc_item
			):
				frappe.throw(
					_(
						"{0}: Payment Entry and Payment Entry Deduction references must be provided together."
					).format(row_label)
				)

			if item.reference_doc_item in seen_deductions:
				frappe.throw(
					_("{0}: Payment Entry Deduction {1} is referenced more than once.").format(
						row_label, frappe.bold(item.reference_doc_item)
					)
				)
			seen_deductions.add(item.reference_doc_item)
			payment_entry_rows.append(item)

		if not payment_entry_rows:
			return

		payment_entries = {}
		for payment_entry_name in sorted({item.reference_doc for item in payment_entry_rows}):
			payment_entry = frappe.get_doc("Payment Entry", payment_entry_name, for_update=True)
			payment_entry.check_permission("read")
			payment_entries[payment_entry_name] = payment_entry

		for item in payment_entry_rows:
			row_label = _("Row {0}").format(item.idx)
			payment_entry = payment_entries[item.reference_doc]
			if (
				payment_entry.docstatus != 1
				or payment_entry.payment_type != self.payment_type
				or payment_entry.party_type != self.party_type
				or payment_entry.company != self.company
				or payment_entry.party != self.get(self.party_field)
			):
				frappe.throw(
					_("{0}: Payment Entry {1} does not match this Company and {2}.").format(
						row_label, frappe.bold(payment_entry.name), _(self.party_type)
					)
				)

			deduction = next(
				(
					deduction
					for deduction in payment_entry.get("deductions") or []
					if deduction.name == item.reference_doc_item
				),
				None,
			)
			if not deduction or not deduction.custom_is_withholding_tax_entry:
				frappe.throw(
					_(
						"{0}: Payment Entry Deduction {1} is not an eligible withholding tax deduction."
					).format(row_label, frappe.bold(item.reference_doc_item))
				)

		existing_references = frappe.get_all(
			"Withholding Tax Entry Item",
			filters={
				"reference_doc_item_doctype": "Payment Entry Deduction",
				"reference_doc_item": ["in", list(seen_deductions)],
				"parenttype": [
					"in",
					["Sales Withholding Tax Entry", "Purchase Withholding Tax Entry"],
				],
				"docstatus": ["<", 2],
			},
			fields=["reference_doc_item", "parent", "parenttype"],
		)
		for reference in existing_references:
			if reference.parent == self.name and reference.parenttype == self.doctype:
				continue
			frappe.throw(
				_("Payment Entry Deduction {0} is already referenced by {1} {2}.").format(
					frappe.bold(reference.reference_doc_item),
					_(reference.parenttype),
					frappe.bold(reference.parent),
				)
			)

	def calculate_totals(self) -> None:
		precision = self.precision("tax_amount", "items")
		for item in self.items:
			item.tax_amount = flt(flt(item.base_amount) * flt(item.tax_rate) / 100, precision)

		self.total_base_amount = flt(
			sum(flt(item.base_amount) for item in self.items), self.precision("total_base_amount")
		)
		self.total_tax_amount = flt(
			sum(flt(item.tax_amount) for item in self.items), self.precision("total_tax_amount")
		)

	def validate_party_address(self) -> None:
		party = self.get(self.party_field)
		address = self.get(self.address_field)
		if not party or not address:
			return
		if not frappe.db.exists(
			"Dynamic Link",
			{
				"parent": address,
				"parenttype": "Address",
				"link_doctype": self.party_type,
				"link_name": party,
			},
		):
			frappe.throw(
				_("Address {0} is not linked to {1} {2}.").format(
					frappe.bold(address), _(self.party_type), frappe.bold(party)
				)
			)

	def validate_item(self, item: "WithholdingTaxEntryItem", row_label: str) -> None:
		for fieldname in ("income_type", "base_amount", "tax_rate", "tax_amount"):
			if item.get(fieldname) in (None, ""):
				frappe.throw(_("{0}: {1} is required.").format(row_label, _(item.meta.get_label(fieldname))))

		if flt(item.base_amount) <= 0:
			frappe.throw(_("{0}: Base Amount must be greater than zero.").format(row_label))
		if not 0 < flt(item.tax_rate) <= 100:
			frappe.throw(
				_("{0}: Tax Rate must be greater than zero and no greater than 100.").format(row_label)
			)
		if flt(item.tax_amount) <= 0:
			frappe.throw(_("{0}: Tax Amount must be greater than zero.").format(row_label))

	def validate_reference(self, item: "WithholdingTaxEntryItem", row_label: str) -> None:
		if bool(item.reference_doc_doctype) != bool(item.reference_doc):
			frappe.throw(
				_("{0}: Reference Document Type and Reference Document must be provided together.").format(
					row_label
				)
			)
		if bool(item.reference_doc_item_doctype) != bool(item.reference_doc_item):
			frappe.throw(
				_("{0}: Reference Item Type and Reference Item must be provided together.").format(row_label)
			)
		if not item.reference_doc_item:
			return
		if not item.reference_doc:
			frappe.throw(
				_("{0}: A Reference Document is required when a Reference Item is set.").format(row_label)
			)

		reference_item = frappe.db.get_value(
			item.reference_doc_item_doctype,
			item.reference_doc_item,
			["parent", "parenttype"],
			as_dict=True,
		)
		if not reference_item:
			frappe.throw(_("{0}: Reference Item does not exist.").format(row_label))
		if (
			reference_item.parent != item.reference_doc
			or reference_item.parenttype != item.reference_doc_doctype
		):
			frappe.throw(
				_("{0}: Reference Item does not belong to the selected Reference Document.").format(row_label)
			)
