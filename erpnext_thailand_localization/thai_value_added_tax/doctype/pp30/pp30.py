# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.model.document import Document


class PP30(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_thailand_localization.thai_value_added_tax.doctype.pp30_branch.pp30_branch import (
			PP30Branch,
		)
		from erpnext_thailand_localization.thai_value_added_tax.doctype.pp30_purchase_entry.pp30_purchase_entry import (
			PP30PurchaseEntry,
		)
		from erpnext_thailand_localization.thai_value_added_tax.doctype.pp30_sales_entry.pp30_sales_entry import (
			PP30SalesEntry,
		)

		amended_from: DF.Link | None
		branch_no: DF.Data
		branches: DF.Table[PP30Branch]
		carried_forward_credit: DF.Currency
		company: DF.Link
		company_tax_address: DF.Link
		excess_vat: DF.Currency
		excess_vat_before_credit: DF.Currency
		exempt_sales: DF.Currency
		filing_date: DF.Date | None
		input_vat: DF.Currency
		output_vat: DF.Currency
		purchase_amount: DF.Currency
		purchase_entries: DF.Table[PP30PurchaseEntry]
		reference_no: DF.Data | None
		remarks: DF.SmallText | None
		sales_amount: DF.Currency
		sales_entries: DF.Table[PP30SalesEntry]
		tax_id: DF.Data
		tax_month: DF.Literal["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
		tax_year: DF.Int
		taxable_sales: DF.Currency
		taxpayer_name: DF.Data
		use_branch_totals: DF.Check
		vat_payable: DF.Currency
		vat_payable_before_credit: DF.Currency
		zero_rated_sales: DF.Currency
	# end: auto-generated types

	def validate(self):
		if self.use_branch_totals:
			frappe.throw(_("Select VAT Entries instead of manual branch totals."))
		self.set_company_details()
		self.validate_taxpayer()
		self.calculate_from_entries()

	def validate_taxpayer(self):
		if (
			not self.tax_id
			or not self.tax_id.isascii()
			or not self.tax_id.isdigit()
			or len(self.tax_id) != 13
		):
			frappe.throw(_("Tax ID must contain exactly 13 digits."))
		if not 2400 <= self.tax_year <= 2999:
			frappe.throw(_("Tax Year must be a Buddhist Era year between 2400 and 2999."))
		self.validate_branch_number(self.branch_no)

	def validate_branch_number(self, number):
		if not number or not number.isascii() or not number.isdigit() or len(number) > 5:
			frappe.throw(_("Branch Number must contain 1 to 5 digits."))

	def calculate_amounts(self):
		fields = (
			"sales_amount",
			"zero_rated_sales",
			"exempt_sales",
			"output_vat",
			"purchase_amount",
			"input_vat",
		)
		if self.use_branch_totals:
			if not self.branches:
				frappe.throw(_("Add at least one branch when using branch totals."))
			seen = set()
			for row in self.branches:
				self.validate_branch_number(row.branch_no)
				branch = int(row.branch_no)
				if branch in seen:
					frappe.throw(_("Branch Number must not repeat."))
				seen.add(branch)
				if not row.address_number:
					frappe.throw(_("Address Number is required for each branch."))
				if (
					not row.postal_code
					or not row.postal_code.isascii()
					or not row.postal_code.isdigit()
					or len(row.postal_code) != 5
				):
					frappe.throw(_("Postal Code must contain exactly 5 digits."))
				self.calculate_taxable_sales(row, fields)
			for field in fields:
				self.set(field, sum(self.money(row.get(field)) for row in self.branches))
		self.calculate_taxable_sales(self, fields)
		credit = self.money(self.carried_forward_credit)
		self.carried_forward_credit = credit
		difference = self.money(self.output_vat) - self.money(self.input_vat)
		self.vat_payable_before_credit = max(difference, Decimal("0.00"))
		self.excess_vat_before_credit = max(-difference, Decimal("0.00"))
		self.vat_payable = max(difference - credit, Decimal("0.00"))
		self.excess_vat = max(credit - difference, Decimal("0.00"))

	def calculate_taxable_sales(self, target, fields):
		for field in fields:
			target.set(field, self.money(target.get(field)))
		taxable = (
			self.money(target.sales_amount)
			- self.money(target.zero_rated_sales)
			- self.money(target.exempt_sales)
		)
		if taxable < 0:
			frappe.throw(_("Zero-rated and exempt sales must not exceed monthly sales."))
		target.taxable_sales = taxable

	def money(self, value):
		try:
			amount = Decimal(str(value or 0))
			if not amount.is_finite() or amount < 0:
				raise InvalidOperation
			return amount.quantize(Decimal("0.01"))
		except (InvalidOperation, ValueError):
			frappe.throw(_("VAT amounts must be finite, non-negative numbers."))

	def get_period(self):
		from calendar import monthrange
		from datetime import date

		try:
			year, month = int(self.tax_year) - 543, int(self.tax_month)
			return date(year, month, 1), date(year, month, monthrange(year, month)[1])
		except (TypeError, ValueError):
			frappe.throw(_("Select a valid tax year and month."))

	@frappe.whitelist()
	def get_vat_entries(self):
		self.check_permission("write")
		if self.docstatus != 0:
			frappe.throw(_("VAT entries can only be loaded into a draft PP30."))
		start, end = self.get_period()
		if not self.company or not self.company_tax_address:
			frappe.throw(_("Select Company and Company Tax Address first."))
		self.set_company_details()
		for table, doctype in (
			("purchase_entries", "Purchase VAT Entry"),
			("sales_entries", "Sales VAT Entry"),
		):
			self.set(table, [])
			entries = frappe.get_list(
				doctype,
				filters={
					"company": self.company,
					"company_tax_address": self.company_tax_address,
					"report_date": ["between", [start, end]],
					"docstatus": 1,
				},
				fields=["name"],
				order_by="tax_invoice_date, name",
				limit_page_length=0,
			)
			for entry in entries:
				if not self.get_other_return(doctype, entry.name):
					self.append(table, {"vat_entry": entry.name})
		self.calculate_from_entries()

	def get_other_return(self, doctype, name):
		child = "PP30 Purchase Entry" if doctype == "Purchase VAT Entry" else "PP30 Sales Entry"
		parents = frappe.get_all(child, filters={"vat_entry": name, "parenttype": "PP30"}, pluck="parent")
		parents = [parent for parent in parents if parent != self.name]
		if not parents:
			return None
		returns = frappe.qb.DocType("PP30")
		matches = (
			frappe.qb.from_(returns)
			.select(returns.name)
			.where((returns.docstatus == 1) & returns.name.isin(parents))
			.for_update()
			.run()
		)
		return matches[0][0] if matches else None

	def calculate_from_entries(self):
		from frappe.utils import getdate

		start, end = self.get_period()
		for field in (
			"sales_amount",
			"zero_rated_sales",
			"exempt_sales",
			"output_vat",
			"purchase_amount",
			"input_vat",
		):
			self.set(field, Decimal("0.00"))
		for table, doctype in (
			("purchase_entries", "Purchase VAT Entry"),
			("sales_entries", "Sales VAT Entry"),
		):
			seen = set()
			for row in sorted(self.get(table) or [], key=lambda r: r.vat_entry or ""):
				if not row.vat_entry or row.vat_entry in seen:
					frappe.throw(_("Select each VAT Entry only once."))
				seen.add(row.vat_entry)
				entry = frappe.get_doc(doctype, row.vat_entry, for_update=True)
				entry.check_permission("read")
				if entry.docstatus != 1:
					frappe.throw(_("Only submitted VAT Entries can be selected."))
				if entry.company != self.company or entry.company_tax_address != self.company_tax_address:
					frappe.throw(_("VAT Entry must match the PP30 Company and establishment."))
				if not start <= getdate(entry.report_date) <= end:
					frappe.throw(_("VAT Entry must belong to the PP30 reporting period."))
				entry.validate_report_details()
				if (
					entry.company_currency != "THB"
					or entry.company_tax_id != self.tax_id
					or int(entry.company_branch_code) != int(self.branch_no)
				):
					frappe.throw(_("VAT Entry taxpayer details must match PP30 and use THB."))
				if self.get_other_return(doctype, entry.name):
					frappe.throw(_("VAT Entry is already used by another submitted PP30."))
				base, tax = self.signed_money(entry.tax_base), self.signed_money(entry.tax_amount)
				if doctype == "Purchase VAT Entry":
					self.purchase_amount += base
					self.input_vat += tax
				else:
					self.sales_amount += base
					self.output_vat += tax
					if entry.vat_category == "Zero Rated":
						self.zero_rated_sales += base
					elif entry.vat_category == "Exempt":
						self.exempt_sales += base
		self.use_branch_totals = 0
		self.calculate_amounts()

	def signed_money(self, value):
		try:
			amount = Decimal(str(value or 0))
			if not amount.is_finite():
				raise InvalidOperation
			return amount.quantize(Decimal("0.01"))
		except (InvalidOperation, ValueError):
			frappe.throw(_("VAT amounts must be finite numbers."))

	def get_report_entries(self, table):
		if table not in ("purchase_entries", "sales_entries"):
			frappe.throw(_("Invalid VAT entry table."))
		self.check_permission("read")
		doctype = "Purchase VAT Entry" if table == "purchase_entries" else "Sales VAT Entry"
		entries = []
		for row in self.get(table) or []:
			entry = frappe.get_doc(doctype, row.vat_entry)
			entry.check_permission("read")
			entries.append(entry)
		return sorted(entries, key=lambda e: (str(e.tax_invoice_date), e.tax_invoice_number, e.name))

	def set_company_details(self):
		company = frappe.get_doc("Company", self.company)
		company.check_permission("read")
		if company.default_currency != "THB":
			frappe.throw(_("PP30 requires Company currency THB."))
		address = frappe.get_doc("Address", self.company_tax_address)
		address.check_permission("read")
		if not any(row.link_doctype == "Company" and row.link_name == self.company for row in address.links):
			frappe.throw(_("Company Tax Address must belong to the selected Company."))
		if not address.get("branch_code"):
			frappe.throw(_("Company Tax Address must have a Branch Code."))
		self.branch_no = address.branch_code
		self.taxpayer_name = company.company_name
		self.tax_id = company.tax_id
