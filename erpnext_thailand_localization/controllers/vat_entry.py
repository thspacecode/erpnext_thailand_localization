from typing import ClassVar, Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VATEntry(Document):
	party_type: ClassVar[Literal["Customer", "Supplier"]]
	direction: ClassVar[Literal["sales", "purchase"]]

	def validate(self):
		self.validate_account()
		self.validate_source()
		self.validate_amounts()
		self.set_party_details()

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
			self.party_name = party.get(f"{self.party_type.lower()}_name")
			self.tax_id = self.tax_id or party.get("tax_id")
			self.branch_code = self.branch_code or party.get("branch_code")
