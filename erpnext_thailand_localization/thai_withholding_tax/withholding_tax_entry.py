import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WithholdingTaxEntry(Document):
	party_type: str
	party_field: str
	address_field: str

	def validate(self):
		self.calculate_totals()
		if self.docstatus == 1:
			self.validate_submission()

	def calculate_totals(self):
		precision = self.precision("tax_amount", "items")
		for item in self.items:
			item.tax_amount = flt(flt(item.base_amount) * flt(item.tax_rate) / 100, precision)

		self.total_base_amount = flt(
			sum(flt(item.base_amount) for item in self.items), self.precision("total_base_amount")
		)
		self.total_tax_amount = flt(
			sum(flt(item.tax_amount) for item in self.items), self.precision("total_tax_amount")
		)

	def validate_submission(self):
		self.validate_party_address()
		for item in self.items:
			self.validate_item(item)

	def validate_party_address(self):
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

	def validate_item(self, item):
		row_label = _("Row {0}").format(item.idx)
		for fieldname in ("income_type", "base_amount", "tax_rate", "tax_amount", "gl_entry"):
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

		self.validate_reference(item, row_label)
		self.validate_gl_entry(item, row_label)

	def validate_reference(self, item, row_label):
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

	def validate_gl_entry(self, item, row_label):
		gl_entry = frappe.db.get_value(
			"GL Entry",
			item.gl_entry,
			["company", "is_cancelled", "voucher_type", "voucher_no"],
			as_dict=True,
		)
		if not gl_entry:
			frappe.throw(_("{0}: GL Entry does not exist.").format(row_label))
		if gl_entry.is_cancelled:
			frappe.throw(_("{0}: GL Entry is cancelled.").format(row_label))
		if gl_entry.company != self.company:
			frappe.throw(
				_("{0}: GL Entry must belong to Company {1}.").format(row_label, frappe.bold(self.company))
			)
		if self.payment_entry and (
			gl_entry.voucher_type != "Payment Entry" or gl_entry.voucher_no != self.payment_entry
		):
			frappe.throw(
				_("{0}: GL Entry must belong to Payment Entry {1}.").format(
					row_label, frappe.bold(self.payment_entry)
				)
			)
