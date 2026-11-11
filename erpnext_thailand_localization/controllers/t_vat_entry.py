from unittest import TestCase
from unittest.mock import patch

import frappe


class VATEntryTest:
	class TestCase(TestCase):
		def make_entry(self):
			"""Build an unsaved register entry without creating linked master records."""
			return frappe.get_doc(
				doctype=self.entry_doctype,
				company="Example",
				party="Party",
				account="VAT",
				tax_base=100,
				tax_amount=7,
				voucher_type="Journal Entry",
				voucher_no="JE-1",
			)

		def test_validate_amounts(self):
			"""Calculate effective VAT rates for normal, zero-rated, and credit amounts."""
			entry = self.make_entry()
			# Arrange, act, and assert: Preserve signs while deriving the effective rate.
			entry.validate_amounts()
			self.assertEqual(entry.tax_rate, 7)
			entry.tax_amount = 0
			entry.validate_amounts()
			self.assertEqual(entry.tax_rate, 0)
			entry.tax_base, entry.tax_amount = -100, -7
			entry.validate_amounts()
			self.assertEqual(entry.tax_rate, 7)
			entry.tax_amount = 7
			with self.assertRaisesRegex(frappe.ValidationError, "same sign"):
				entry.validate_amounts()
			entry.tax_base = 0
			with self.assertRaisesRegex(frappe.ValidationError, "must not be zero"):
				entry.validate_amounts()

		def test_validate_account(self):
			"""Require the configured active Company-currency ledger account."""
			entry = self.make_entry()
			company = frappe._dict(
				default_currency="THB", **{f"{entry.direction}_value_added_tax_account": "VAT"}
			)
			account = frappe._dict(company="Example", is_group=0, disabled=0, account_currency="THB")
			# Arrange: Mock master lookup only; run the actual account validation.
			with patch("frappe.get_cached_doc", side_effect=[company, account] * 5):
				entry.validate_account()
				self.assertEqual(entry.company_currency, "THB")
				account.disabled = 1
				with self.assertRaisesRegex(frappe.ValidationError, "active ledger account"):
					entry.validate_account()
				account.disabled = 0
				account.account_currency = "USD"
				with self.assertRaisesRegex(frappe.ValidationError, "Company currency"):
					entry.validate_account()
				account.account_currency = "THB"
				account.company = "Other"
				with self.assertRaisesRegex(frappe.ValidationError, "active ledger account"):
					entry.validate_account()
				entry.account = "Undue VAT"
				with self.assertRaisesRegex(frappe.ValidationError, "configured Company VAT account"):
					entry.validate_account()

		def test_validate_source(self):
			"""Reject draft sources, company mismatches, and unrelated accounting links."""
			entry = self.make_entry()
			source = frappe.get_doc(doctype="Journal Entry", company="Example", docstatus=1)
			gl = frappe.get_doc(
				doctype="GL Entry",
				company="Example",
				account="VAT",
				voucher_type="Journal Entry",
				voucher_no="JE-1",
				is_cancelled=0,
			)
			# Arrange: Mock lookups and permission checks, not source validation.
			with (
				patch("frappe.get_doc", side_effect=lambda dt, name: gl if dt == "GL Entry" else source),
				patch.object(type(source), "check_permission"),
				patch.object(type(gl), "check_permission"),
			):
				entry.validate_source()
				source.docstatus = 0
				with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
					entry.validate_source()
				source.docstatus = 1
				source.company = "Other"
				with self.assertRaisesRegex(frappe.ValidationError, "selected Company"):
					entry.validate_source()
				source.company = "Example"
				entry.gl_entry = "GL-1"
				entry.validate_source()
				gl.is_cancelled = 1
				with self.assertRaisesRegex(frappe.ValidationError, "GL Entry must match"):
					entry.validate_source()

		def test_set_party_details(self):
			"""Keep invoice tax details instead of replacing them with current party data."""
			entry = self.make_entry()
			party = frappe.get_doc(
				doctype=entry.party_type,
				**{f"{entry.party_type.lower()}_name": "Party Name", "tax_id": "123"},
			)
			# Arrange: Mock party lookup; test initial defaults and saved snapshots.
			with patch("frappe.get_doc", return_value=party), patch.object(type(party), "check_permission"):
				entry.set_party_details()
				self.assertEqual(entry.party_name, "Party Name")
				self.assertEqual(entry.tax_id, "123")
				entry.tax_id = "INVOICE-TAX-ID"
				entry.set_party_details()
				self.assertEqual(entry.tax_id, "INVOICE-TAX-ID")
				with patch.object(entry, "get_doc_before_save", return_value=frappe._dict(party="Party")):
					party.tax_id = "CHANGED"
					entry.set_party_details()
					self.assertEqual(entry.tax_id, "INVOICE-TAX-ID")
