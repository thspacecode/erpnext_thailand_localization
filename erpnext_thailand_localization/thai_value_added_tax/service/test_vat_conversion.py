from unittest import TestCase
from unittest.mock import patch

import frappe

from erpnext_thailand_localization.thai_value_added_tax.service.vat_conversion import (
	get_undue_vat_conversion_entry,
)


def raise_validation_error(message):
	"""Keep error messages without request-local message handling."""
	raise frappe.ValidationError(message)


class TestVatConversion(TestCase):
	def test_get_undue_vat_conversion_entry(self):
		"""Convert final base taxes, preserve cost centers, and reverse returns and deductions."""
		for doctype, amount, add_deduct, expected_debit, ratio in (
			("Sales Invoice", 70, "Add", 70, 1),
			("Purchase Invoice", 70, "Add", -70, 1),
			("Sales Invoice", -70, "Add", -70, 1),
			("Purchase Invoice", -70, "Add", 70, 1),
			("Purchase Invoice", 70, "Deduct", 70, 1),
			("Sales Invoice", 70, "Add", 35, 0.5),
			("Purchase Invoice", 70, "Add", -35, 0.5),
			("Sales Invoice", 70, "Add", 23.33, 1 / 3),
		):
			with self.subTest(doctype=doctype, amount=amount, add_deduct=add_deduct):
				# Arrange: Mock only reads and eligibility; use final base amounts, not rates.
				invoice = frappe._dict(
					doctype=doctype,
					company="Example",
					name="INV-1",
					posting_date="2026-01-01",
					currency="USD",
					conversion_rate=35,
					items=[],
					taxes=[
						frappe._dict(
							account_head="Undue",
							base_tax_amount_after_discount_amount=amount,
							tax_amount=2,
							base_tax_amount=100,
							cost_center="Tax Center",
							add_deduct_tax=add_deduct,
						),
						frappe._dict(account_head="Other", base_tax_amount_after_discount_amount=999),
					],
				)
				company = frappe._dict(
					default_currency="THB",
					undue_sales_value_added_tax_account="Undue",
					sales_value_added_tax_account="VAT",
					undue_purchase_value_added_tax_account="Undue",
					purchase_value_added_tax_account="VAT",
				)
				account = frappe._dict(company="Example", is_group=0, disabled=0, account_currency="THB")
				with (
					patch(
						"erpnext_thailand_localization.thai_value_added_tax.service.vat_conversion.frappe.get_cached_doc",
						side_effect=[company, account, account],
					),
					patch(
						"erpnext_thailand_localization.thai_value_added_tax.service.vat_conversion.validate_undue_vat_items"
					) as validate,
					patch.object(frappe, "get_doc") as get_doc,
				):
					# Act: Build a plain payload; never create or save a Document.
					entry = get_undue_vat_conversion_entry(invoice, conversion_ratio=ratio)
					# Assert: Exactly one balanced pair uses company currency and final tax.
					self.assertEqual(entry["doctype"], "Journal Entry")
					self.assertEqual(entry["posting_date"], invoice.posting_date)
					self.assertEqual(len(entry["accounts"]), 2)
					undue, vat = entry["accounts"]
					self.assertEqual(undue["account"], "Undue")
					self.assertEqual(vat["account"], "VAT")
					self.assertEqual(
						undue["debit_in_account_currency"] - undue["credit_in_account_currency"],
						expected_debit,
					)
					self.assertEqual(
						vat["debit_in_account_currency"] - vat["credit_in_account_currency"], -expected_debit
					)
					self.assertEqual(undue["cost_center"], "Tax Center")
					self.assertEqual(vat["account_currency"], "THB")
					validate.assert_called_once_with(invoice)
					get_doc.assert_not_called()

	def test_get_undue_vat_conversion_entry_validation(self):
		"""Reject unsupported documents, missing configuration, and empty conversion amounts."""
		# Arrange: No database writes; isolate input guards with mocked reads.
		invoice = frappe._dict(doctype="Sales Invoice", company="Example", taxes=[])
		company = frappe._dict(default_currency="THB")
		account = frappe._dict(company="Example", is_group=0, disabled=0, account_currency="THB")
		with (
			patch.object(frappe, "throw", side_effect=raise_validation_error),
			patch(
				"erpnext_thailand_localization.thai_value_added_tax.service.vat_conversion.validate_undue_vat_items"
			),
			patch.object(
				frappe, "get_cached_doc", side_effect=lambda dt, name: company if dt == "Company" else account
			),
		):
			# Act and assert: Each guard has a specific error.
			with self.assertRaisesRegex(frappe.ValidationError, "ratio must be greater than zero"):
				get_undue_vat_conversion_entry(invoice, conversion_ratio=0)
			with self.assertRaisesRegex(frappe.ValidationError, "ratio must be greater than zero"):
				get_undue_vat_conversion_entry(invoice, conversion_ratio=1.1)
			with self.assertRaisesRegex(frappe.ValidationError, "Set both undue VAT and VAT accounts"):
				get_undue_vat_conversion_entry(invoice)
			company.update(undue_sales_value_added_tax_account="Undue", sales_value_added_tax_account="Undue")
			with self.assertRaisesRegex(frappe.ValidationError, "accounts must be different"):
				get_undue_vat_conversion_entry(invoice)
			company.sales_value_added_tax_account = "VAT"
			with self.assertRaisesRegex(frappe.ValidationError, "no non-zero undue VAT"):
				get_undue_vat_conversion_entry(invoice)
			account.account_currency = "USD"
			with self.assertRaisesRegex(frappe.ValidationError, "must use the Company currency"):
				get_undue_vat_conversion_entry(invoice)
			invoice.doctype = "Sales Order"
			with self.assertRaisesRegex(
				frappe.ValidationError, "Expected a Sales Invoice or Purchase Invoice"
			):
				get_undue_vat_conversion_entry(invoice)
