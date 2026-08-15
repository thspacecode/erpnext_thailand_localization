from math import ceil

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, getdate

from erpnext_thailand_localization.service.utils import (
	normalize_branch_code,
	normalize_digits,
	validate_branch_code,
	validate_tax_id,
)
from erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing import get_income_type_pnd


class PNDFiling(Document):
	pnd_type: str
	item_doctype: str
	legal_bases: tuple[str, ...]
	rows_per_attachment_page = 6

	def validate(self) -> None:
		self.normalize_period()
		self.validate_filing_details()
		self.set_company_snapshot()
		self.set_item_snapshots()
		self.calculate_totals()

	def before_submit(self) -> None:
		self.validate_required_tax_data()
		self.validate_sources()
		self.validate_duplicate_sources()

	def normalize_period(self) -> None:
		if self.tax_period:
			self.tax_period = get_first_day(getdate(self.tax_period))

	def validate_filing_details(self) -> None:
		if self.legal_basis not in self.legal_bases:
			frappe.throw(
				_("Legal Basis {0} is not valid for {1}.").format(
					frappe.bold(self.legal_basis), frappe.bold(self.pnd_type)
				)
			)

		if self.filing_type == "Additional":
			if not self.additional_filing_no or self.additional_filing_no < 1:
				frappe.throw(_("Additional Filing No. must be greater than zero for an additional filing."))
		else:
			self.additional_filing_no = 0

		if not self.company or not self.tax_period:
			return

		filters = {
			"company": self.company,
			"tax_period": self.tax_period,
			"filing_type": self.filing_type,
			"additional_filing_no": self.additional_filing_no,
			"docstatus": ["!=", 2],
			"name": ["!=", self.name],
		}
		if duplicate := frappe.db.exists(self.doctype, filters):
			frappe.throw(
				_("A {0} filing already exists for this company, period, and filing number: {1}.").format(
					frappe.bold(self.pnd_type), frappe.bold(duplicate)
				)
			)

	def set_company_snapshot(self) -> None:
		if not self.company:
			return

		company = frappe.get_cached_doc("Company", self.company)
		self.company_name = company.company_name
		self.company_currency = company.default_currency
		self.company_tax_id = normalize_digits(company.tax_id)
		if not self.company_address:
			self.company_address = get_default_address("Company", self.company)
		if not self.company_address:
			return

		self.validate_linked_address("Company", self.company, self.company_address)
		address = frappe.get_cached_doc("Address", self.company_address)
		self.company_branch_code = normalize_branch_code(
			self.company_branch_code or address.get("branch_code")
		)
		self.company_address_line1 = address.address_line1
		self.company_address_line2 = address.address_line2
		self.company_subdistrict = address.city
		self.company_district = address.county
		self.company_province = address.state
		self.company_postal_code = address.pincode
		self.company_country = address.country

	def set_item_snapshots(self) -> None:
		for item in self.items:
			if not item.purchase_withholding_tax_entry or not item.withholding_tax_entry_item:
				continue

			source = frappe.get_doc("Purchase Withholding Tax Entry", item.purchase_withholding_tax_entry)
			source_item = next(
				(row for row in source.items if row.name == item.withholding_tax_entry_item), None
			)
			if not source_item:
				continue

			item.payment_date = source.payment_date
			item.supplier = source.supplier
			item.supplier_address = source.supplier_address
			item.income_type = source_item.income_type
			item.income_description = source_item.income_type
			item.base_amount = source_item.base_amount
			item.tax_rate = source_item.tax_rate
			item.tax_amount = source_item.tax_amount
			item.reference_doc_doctype = source_item.reference_doc_doctype
			item.reference_doc = source_item.reference_doc
			item.reference_doc_item_doctype = source_item.reference_doc_item_doctype
			item.reference_doc_item = source_item.reference_doc_item

			supplier = frappe.get_cached_doc("Supplier", source.supplier)
			item.recipient_name = supplier.supplier_name
			item.recipient_tax_id = normalize_digits(supplier.tax_id)
			if source.supplier_address:
				self.validate_linked_address("Supplier", source.supplier, source.supplier_address)
				address = frappe.get_cached_doc("Address", source.supplier_address)
				item.recipient_branch_code = normalize_branch_code(
					item.recipient_branch_code or address.get("branch_code")
				)
				item.address_line1 = address.address_line1
				item.address_line2 = address.address_line2
				item.subdistrict = address.city
				item.district = address.county
				item.province = address.state
				item.postal_code = address.pincode
				item.country = address.country

			if self.pnd_type == "PND 3" and not (item.recipient_first_name or item.recipient_last_name):
				first_name, _, last_name = supplier.supplier_name.rpartition(" ")
				item.recipient_first_name = first_name or last_name
				item.recipient_last_name = last_name if first_name else None

	def calculate_totals(self) -> None:
		self.total_base_amount = flt(
			sum(flt(item.base_amount) for item in self.items), self.precision("total_base_amount")
		)
		self.total_tax_amount = flt(
			sum(flt(item.tax_amount) for item in self.items), self.precision("total_tax_amount")
		)
		self.surcharge_amount = flt(self.surcharge_amount, self.precision("surcharge_amount"))
		self.grand_total = flt(self.total_tax_amount + self.surcharge_amount, self.precision("grand_total"))
		recipients = {
			(item.recipient_tax_id, item.recipient_branch_code)
			for item in self.items
			if item.recipient_tax_id
		}
		self.recipient_count = len(recipients)
		self.attachment_page_count = (
			ceil(len(recipients) / self.rows_per_attachment_page) if recipients else 0
		)

	def validate_required_tax_data(self) -> None:
		validate_tax_id(self.company_tax_id, _("Company Tax ID"))
		validate_branch_code(self.company_branch_code, _("Company Branch Code"))
		if not self.items:
			frappe.throw(_("At least one withholding tax item is required."))

		for item in self.items:
			row_label = _("Row {0}").format(item.idx)
			validate_tax_id(item.recipient_tax_id, _("{0}: Recipient Tax ID").format(row_label))
			validate_branch_code(
				item.recipient_branch_code, _("{0}: Recipient Branch Code").format(row_label)
			)
			if flt(item.base_amount) <= 0 or flt(item.tax_amount) <= 0:
				frappe.throw(
					_("{0}: Base Amount and Tax Amount must be greater than zero.").format(row_label)
				)
			if not 0 < flt(item.tax_rate) <= 100:
				frappe.throw(
					_("{0}: Tax Rate must be greater than zero and no greater than 100.").format(row_label)
				)

	def validate_sources(self) -> None:
		for item in self.items:
			row_label = _("Row {0}").format(item.idx)
			source = frappe.get_doc("Purchase Withholding Tax Entry", item.purchase_withholding_tax_entry)
			if source.docstatus != 1:
				frappe.throw(_("{0}: Purchase Withholding Tax Entry must be submitted.").format(row_label))
			if source.company != self.company:
				frappe.throw(_("{0}: Source company does not match the return company.").format(row_label))
			if get_first_day(getdate(source.payment_date)) != getdate(self.tax_period):
				frappe.throw(_("{0}: Source payment date is outside the filing period.").format(row_label))
			source_item = next(
				(row for row in source.items if row.name == item.withholding_tax_entry_item), None
			)
			if not source_item:
				frappe.throw(
					_("{0}: Withholding Tax Entry Item does not belong to the selected source.").format(
						row_label
					)
				)
			category = frappe.get_cached_value(
				"Supplier", source.supplier, "custom_thai_withholding_tax_category"
			)
			mapped_pnd = get_income_type_pnd(source_item.income_type, category)
			if mapped_pnd != self.pnd_type:
				frappe.throw(
					_("{0}: Income Type and supplier category map to {1}, not {2}.").format(
						row_label, frappe.bold(mapped_pnd or _("no PND form")), frappe.bold(self.pnd_type)
					)
				)

	def validate_duplicate_sources(self) -> None:
		current_sources = [item.withholding_tax_entry_item for item in self.items]
		if len(current_sources) != len(set(current_sources)):
			frappe.throw(_("The same Withholding Tax Entry Item cannot be included more than once."))

		for item in self.items:
			for item_doctype in ("Thai PND 3 Filing Item", "Thai PND 53 Filing Item"):
				duplicate = frappe.db.get_value(
					item_doctype,
					{
						"withholding_tax_entry_item": item.withholding_tax_entry_item,
						"parent": ["!=", self.name],
						"parenttype": item_doctype.removesuffix(" Item"),
						"docstatus": 1,
					},
					"parent",
				)
				if duplicate:
					frappe.throw(
						_("Withholding Tax Entry Item {0} is already filed in {1}.").format(
							frappe.bold(item.withholding_tax_entry_item), frappe.bold(duplicate)
						)
					)

	@staticmethod
	def validate_linked_address(link_doctype: str, link_name: str, address: str) -> None:
		if not frappe.db.exists(
			"Dynamic Link",
			{
				"parent": address,
				"parenttype": "Address",
				"link_doctype": link_doctype,
				"link_name": link_name,
			},
		):
			frappe.throw(
				_("Address {0} is not linked to {1} {2}.").format(
					frappe.bold(address), _(link_doctype), frappe.bold(link_name)
				)
			)
