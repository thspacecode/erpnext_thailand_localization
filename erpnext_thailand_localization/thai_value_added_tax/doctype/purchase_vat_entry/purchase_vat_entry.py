# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from frappe import _
from frappe.utils import flt, getdate

from erpnext_thailand_localization.controllers.vat_entry import VATEntry
from erpnext_thailand_localization.thai_value_added_tax.service.purchase_vat import get_purchase_vat_rows
from erpnext_thailand_localization.thai_value_added_tax.service.vat_entry import generation_key, group_rows


class PurchaseVATEntry(VATEntry):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		amended_from: DF.Link | None
		branch_code: DF.Data | None
		company: DF.Link
		company_address_display: DF.SmallText | None
		company_branch_code: DF.Data | None
		company_currency: DF.Link | None
		company_tax_address: DF.Link | None
		company_tax_id: DF.Data | None
		company_taxpayer_name: DF.Data | None
		conversion_cost_center: DF.Link | None
		generation_key: DF.Data | None
		gl_entry: DF.Link | None
		naming_series: DF.Literal["PVAT-.YYYY.-.#####"]
		party: DF.Link
		party_name: DF.Data | None
		remarks: DF.SmallText | None
		report_date: DF.Date | None
		source_identity: DF.Data | None
		tax_amount: DF.Currency
		tax_base: DF.Currency
		tax_id: DF.Data | None
		tax_invoice_attachment: DF.Attach | None
		tax_invoice_book: DF.Data | None
		tax_invoice_date: DF.Date | None
		tax_invoice_number: DF.Data | None
		tax_rate: DF.Percent
		undue_vat_account: DF.Link | None
		vat_category: DF.Literal["Taxable", "Zero Rated", "Exempt"]
		voucher_no: DF.DynamicLink
		voucher_type: DF.Link
	# end: auto-generated types

	party_type = "Supplier"
	direction = "purchase"

	def validate(self):
		super().validate()
		self.validate_conversion()

	def validate_conversion(self):
		"""Tie conversion amounts and accounts to the submitted source tax rows."""
		previous = self.get_doc_before_save()
		if (
			previous
			and previous.undue_vat_account
			and (
				getdate(self.tax_invoice_date) != getdate(previous.tax_invoice_date)
				or any(
					self.get(field) != previous.get(field)
					for field in (
						"undue_vat_account",
						"account",
						"conversion_cost_center",
						"tax_base",
						"tax_amount",
						"voucher_type",
						"voucher_no",
						"party",
						"tax_invoice_number",
					)
				)
			)
		):
			frappe.throw(_("Generated purchase VAT conversion details cannot be changed."))
		if not self.undue_vat_account:
			return
		if self.voucher_type != "Purchase Invoice" or not self.generation_key:
			frappe.throw(_("Purchase VAT conversion requires a generated Purchase Invoice source."))
		invoice = frappe.get_doc(self.voucher_type, self.voucher_no, for_update=True)
		if (
			self.party != invoice.supplier
			or self.tax_invoice_number != invoice.bill_no
			or not self.tax_invoice_date
			or getdate(self.tax_invoice_date) != getdate(invoice.bill_date)
		):
			frappe.throw(_("Purchase VAT conversion tax invoice details must match the source invoice."))
		company = frappe.get_cached_doc("Company", self.company)
		if self.undue_vat_account != company.undue_purchase_value_added_tax_account:
			frappe.throw(_("Select the configured Company undue purchase VAT account."))
		account = frappe.get_cached_doc("Account", self.undue_vat_account)
		if (
			account.company != self.company
			or account.is_group
			or account.disabled
			or account.account_currency != company.default_currency
			or self.undue_vat_account == self.account
		):
			frappe.throw(_("Conversion requires a separate active undue VAT account in Company currency."))
		taxes = [row for row in invoice.taxes if row.account_head == self.undue_vat_account]
		rows = get_purchase_vat_rows(
			invoice,
			taxes,
			tax_invoice_number=self.tax_invoice_number,
			tax_invoice_date=self.tax_invoice_date,
			report_date=self.report_date,
		)
		matches = [
			row
			for row in group_rows(rows)
			if generation_key(
				invoice.doctype,
				invoice.name,
				hashlib.sha256(json.dumps(sorted(row.identities)).encode()).hexdigest(),
			)
			== self.generation_key
		]
		if (
			len(matches) != 1
			or any(
				flt(self.get(field), 2) != flt(matches[0].get(field), 2)
				for field in ("tax_base", "tax_amount")
			)
			or self.conversion_cost_center != matches[0].get("conversion_cost_center")
		):
			frappe.throw(_("Purchase VAT conversion must match the source invoice tax amounts."))

	def on_submit(self):
		"""Post conversion only; ordinary register entries do not create another ledger."""
		if not self.undue_vat_account:
			return
		entries = []
		for account, debit in ((self.account, self.tax_amount), (self.undue_vat_account, -self.tax_amount)):
			entries.append(
				frappe._dict(
					company=self.company,
					posting_date=self.report_date,
					voucher_type=self.doctype,
					voucher_no=self.name,
					account=account,
					account_currency=self.company_currency,
					debit=max(debit, 0),
					credit=max(-debit, 0),
					debit_in_account_currency=max(debit, 0),
					credit_in_account_currency=max(-debit, 0),
					debit_in_transaction_currency=max(debit, 0),
					credit_in_transaction_currency=max(-debit, 0),
					transaction_currency=self.company_currency,
					transaction_exchange_rate=1,
					cost_center=self.conversion_cost_center,
					remarks=f"Purchase VAT conversion for {self.voucher_no}",
					is_opening="No",
					against=self.undue_vat_account if account == self.account else self.account,
				)
			)
		make_gl_entries(entries, merge_entries=False)

	def on_cancel(self):
		"""Reverse persisted GL, not current Company account settings."""
		if self.undue_vat_account:
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
			self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
