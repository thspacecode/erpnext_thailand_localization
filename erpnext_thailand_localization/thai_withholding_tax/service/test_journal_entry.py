import uuid
from typing import TYPE_CHECKING

import frappe
from frappe.utils import getdate

from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.service.journal_entry import (
	add_pnd_filing_to_journal_entry,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling


class TestPNDJournalEntry(ERPNextThaiTestSuite):
	company = "Dunder Mifflin"

	def create_filing(
		self,
		doctype: str = "Thai PND 3 Filing",
		docstatus: int = 1,
		surcharge_amount: float = 0,
	) -> "PNDFiling":
		prefix = "PND3" if doctype == "Thai PND 3 Filing" else "PND53"
		filing = frappe.get_doc(
			{
				"doctype": doctype,
				"name": f"_TEST-{prefix}-{uuid.uuid4().hex[:10]}",
				"docstatus": docstatus,
				"company": self.company,
				"currency": "THB",
				"filed_date": "2026-09-07",
				"total_tax_amount": 30,
				"surcharge_amount": surcharge_amount,
				"grand_total": 30 + surcharge_amount,
			}
		)
		filing.db_insert()
		return filing

	def test_add_pnd_filings_to_journal_entry(self) -> None:
		for doctype, tax_account in (
			(
				"Thai PND 3 Filing",
				"Purchase Withholding Tax PND 3 Payable - DM",
			),
			(
				"Thai PND 53 Filing",
				"Purchase Withholding Tax PND 53 Payable - DM",
			),
		):
			with self.subTest(doctype=doctype):
				filing = self.create_filing(doctype)
				journal_entry = add_pnd_filing_to_journal_entry(doctype, filing.name)

				self.assertEqual(journal_entry.company, self.company)
				self.assertEqual(journal_entry.posting_date, getdate("2026-09-07"))
				self.assertEqual(journal_entry.custom_reference_doctype, doctype)
				self.assertEqual(journal_entry.custom_reference_doc, filing.name)
				self.assertEqual(len(journal_entry.accounts), 2)
				self.assertEqual(journal_entry.accounts[0].account, tax_account)
				self.assertEqual(journal_entry.accounts[0].debit_in_account_currency, 30)
				self.assertEqual(journal_entry.accounts[1].account, "Creditors - DM")
				self.assertEqual(journal_entry.accounts[1].party_type, "Supplier")
				self.assertEqual(journal_entry.accounts[1].party, "Revenue Department")
				self.assertEqual(journal_entry.accounts[1].credit_in_account_currency, 30)
				self.assertEqual(journal_entry.total_debit, 30)
				self.assertEqual(journal_entry.total_credit, 30)

	def test_mapping_removes_the_initial_empty_account_row(self) -> None:
		filing = self.create_filing()
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.company = self.company
		journal_entry.append(
			"accounts",
			{
				"account_currency": "THB",
				"exchange_rate": 1,
				"cost_center": "Main - DM",
			},
		)

		journal_entry = add_pnd_filing_to_journal_entry(filing.doctype, filing.name, journal_entry)

		self.assertEqual(len(journal_entry.accounts), 2)
		self.assertTrue(all(row.account for row in journal_entry.accounts))

	def test_submitted_journal_entry_creates_revenue_department_payable(self) -> None:
		filing = self.create_filing()
		journal_entry = add_pnd_filing_to_journal_entry(filing.doctype, filing.name)
		journal_entry.insert()
		journal_entry.submit()

		payable = frappe.db.get_value(
			"GL Entry",
			{
				"voucher_type": "Journal Entry",
				"voucher_no": journal_entry.name,
				"party_type": "Supplier",
				"party": "Revenue Department",
				"is_cancelled": 0,
			},
			["account", "credit", "against_voucher_type", "against_voucher"],
			as_dict=True,
		)
		self.assertEqual(payable.account, "Creditors - DM")
		self.assertEqual(payable.credit, 30)
		self.assertFalse(payable.against_voucher_type)
		self.assertFalse(payable.against_voucher)

	def test_surcharge_adds_an_expense_account_placeholder(self) -> None:
		filing = self.create_filing(surcharge_amount=5)

		journal_entry = add_pnd_filing_to_journal_entry(filing.doctype, filing.name)

		self.assertEqual(len(journal_entry.accounts), 3)
		self.assertFalse(journal_entry.accounts[1].account)
		self.assertEqual(journal_entry.accounts[1].debit_in_account_currency, 5)
		self.assertEqual(journal_entry.accounts[2].credit_in_account_currency, 35)
		self.assertEqual(journal_entry.total_debit, 35)
		self.assertEqual(journal_entry.total_credit, 35)

	def test_filing_cannot_be_added_twice(self) -> None:
		filing = self.create_filing()
		journal_entry = add_pnd_filing_to_journal_entry(filing.doctype, filing.name)

		with self.assertRaisesRegex(frappe.ValidationError, "already been added"):
			add_pnd_filing_to_journal_entry(filing.doctype, filing.name, journal_entry)

		journal_entry.insert()
		with self.assertRaisesRegex(frappe.ValidationError, "already linked to Journal Entry"):
			add_pnd_filing_to_journal_entry(filing.doctype, filing.name)

	def test_journal_entry_can_reference_only_one_filing(self) -> None:
		pnd3_filing = self.create_filing()
		pnd53_filing = self.create_filing("Thai PND 53 Filing")
		journal_entry = add_pnd_filing_to_journal_entry(pnd3_filing.doctype, pnd3_filing.name)

		with self.assertRaisesRegex(frappe.ValidationError, "only one PND Filing"):
			add_pnd_filing_to_journal_entry(pnd53_filing.doctype, pnd53_filing.name, journal_entry)

	def test_filing_must_be_submitted(self) -> None:
		filing = self.create_filing(docstatus=0)

		with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
			add_pnd_filing_to_journal_entry(filing.doctype, filing.name)

	def test_uses_configured_revenue_department_supplier(self) -> None:
		with self.change_settings(
			"Thai Localization Settings",
			revenue_department="Hammermill Paper Company",
		):
			filing = self.create_filing()
			journal_entry = add_pnd_filing_to_journal_entry(filing.doctype, filing.name)

			self.assertEqual(journal_entry.accounts[-1].party, "Hammermill Paper Company")

	def test_revenue_department_supplier_must_be_configured(self) -> None:
		with self.change_settings("Thai Localization Settings", revenue_department=None):
			filing = self.create_filing()

			with self.assertRaisesRegex(frappe.ValidationError, "Please set Revenue Department"):
				add_pnd_filing_to_journal_entry(filing.doctype, filing.name)
