from math import isfinite
from typing import ClassVar, Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VATEntry(Document):
	party_type: ClassVar[Literal["Customer", "Supplier"]]
	direction: ClassVar[Literal["sales", "purchase"]]

	def validate(self):
		previous = self.get_doc_before_save()
		if previous and any(
			self.get(field) != previous.get(field) for field in ("generation_key", "source_identity")
		):
			frappe.throw(_("Generated VAT source identity cannot be changed."))
		self.validate_account()
		self.validate_source()
		self.validate_amounts()
		self.set_party_details()
		if self.company_tax_address:
			self.set_company_details()

	def validate_account(self):
		company = frappe.get_cached_doc("Company", self.company)
		account = frappe.get_cached_doc("Account", self.account)
		if self.account != company.get(f"{self.direction}_value_added_tax_account"):
			frappe.throw(_("Select the configured Company VAT account."))
		if account.company != self.company or account.is_group or account.disabled:
			frappe.throw(_("VAT account must be an active ledger account in the selected Company."))
		if account.account_currency != company.default_currency:
			frappe.throw(_("VAT account must use the Company currency."))
		self.company_currency = company.default_currency

	def validate_source(self):
		if self.voucher_type not in (
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
			"Expense Claim",
		):
			frappe.throw(_("Unsupported VAT source document type."))
		source = frappe.get_doc(self.voucher_type, self.voucher_no)
		source.check_permission("read")
		if source.company != self.company or source.docstatus != 1:
			frappe.throw(_("VAT source must be submitted and belong to the selected Company."))
		if self.gl_entry:
			gl = frappe.get_doc("GL Entry", self.gl_entry)
			gl.check_permission("read")
			if (
				gl.company != self.company
				or gl.account != self.account
				or gl.voucher_type != self.voucher_type
				or gl.voucher_no != self.voucher_no
				or gl.is_cancelled
			):
				frappe.throw(
					_("GL Entry must match the VAT account and source document and must not be cancelled.")
				)

	def validate_amounts(self):
		if not all(isfinite(flt(self.get(field))) for field in ("tax_base", "tax_amount")):
			frappe.throw(_("VAT amounts must be finite numbers."))
		if not flt(self.tax_base):
			frappe.throw(_("Tax base must not be zero."))
		if flt(self.tax_base) * flt(self.tax_amount) < 0:
			frappe.throw(_("Tax base and VAT amount must have the same sign."))
		self.tax_rate = flt(flt(self.tax_amount) / flt(self.tax_base) * 100, 6)

	def set_party_details(self):
		party = frappe.get_doc(self.party_type, self.party)
		party.check_permission("read")
		previous = self.get_doc_before_save()
		if not previous or previous.party != self.party:
			self.party_name = self.party_name or party.get(f"{self.party_type.lower()}_name")
			self.tax_id = self.tax_id or party.get("tax_id")
			self.branch_code = self.branch_code or party.get("branch_code")

	def before_submit(self):
		self.set_party_details()
		self.set_company_details()
		self.validate_report_details()

	def before_cancel(self):
		frappe.get_doc(self.doctype, self.name, for_update=True)
		child = "PP30 Purchase Entry" if self.direction == "purchase" else "PP30 Sales Entry"
		rows = frappe.get_all(child, filters={"vat_entry": self.name, "parenttype": "PP30"}, pluck="parent")
		if rows and frappe.db.exists("PP30", {"name": ["in", rows], "docstatus": 1}):
			frappe.throw(_("Cancel the submitted PP30 before cancelling this VAT Entry."))

	def set_company_details(self):
		company = frappe.get_doc("Company", self.company)
		company.check_permission("read")
		if company.default_currency != "THB":
			frappe.throw(_("VAT reporting requires Company currency THB."))
		if not self.company_tax_address:
			frappe.throw(_("Select a Company Tax Address before submitting."))
		address = frappe.get_doc("Address", self.company_tax_address)
		address.check_permission("read")
		if not any(row.link_doctype == "Company" and row.link_name == self.company for row in address.links):
			frappe.throw(_("Company Tax Address must belong to the selected Company."))
		self.company_taxpayer_name = company.company_name
		self.company_tax_id = company.tax_id
		self.company_branch_code = address.get("branch_code")
		self.company_address_display = ", ".join(
			str(address.get(field))
			for field in ("address_line1", "address_line2", "city", "state", "pincode", "country")
			if address.get(field)
		)

	def validate_report_details(self):
		for field in ("tax_invoice_number", "tax_invoice_date", "report_date"):
			if not self.get(field):
				frappe.throw(_("Tax invoice number, date and report date are required before submission."))
		for label, value in ((_("Tax ID"), self.tax_id), (_("Company Tax ID"), self.company_tax_id)):
			if not value or not value.isascii() or not value.isdigit() or len(value) != 13:
				frappe.throw(_("{0} must contain exactly 13 digits.").format(label))
		for label, value in (
			(_("Branch Code"), self.branch_code),
			(_("Company Branch Code"), self.company_branch_code),
		):
			if not value or not value.isascii() or not value.isdigit() or len(value) > 5:
				frappe.throw(_("{0} must contain 1 to 5 digits.").format(label))
		if not self.party_name:
			frappe.throw(_("Party Name is required for VAT reporting."))
		if self.vat_category != "Taxable" and flt(self.tax_amount):
			frappe.throw(_("Zero-rated and exempt entries must have zero VAT."))
