from unittest import TestCase
from unittest.mock import patch

import frappe

from erpnext_thailand_localization.thai_wht.service.withholding_tax import (
	fetch_wht_detail,
	get_reference_withholding_tax_deductions,
	is_withholding_tax_payer_eligible,
)


class TestWithholdingTaxPayer(TestCase):
	def test_is_withholding_tax_payer_eligible(self):
		"""Check payer identity without treating individual recipients as exempt."""
		# Arrange: Mock only the identity lookup; no tax configuration is needed.
		for party_type, value, expected in (
			("Supplier", "Individual - Domestic", False),
			("Supplier", "Juristic Person - Domestic", True),
			("Customer", "Individual", False),
			("Customer", "Company", True),
			("Customer", "Partnership", True),
		):
			with self.subTest(party_type=party_type, value=value):
				with patch.object(frappe, "get_cached_value", return_value=value) as lookup:
					# Act and assert: Only the payer identity controls the exemption.
					self.assertEqual(
						is_withholding_tax_payer_eligible(party_type, "Party", "Company"), expected
					)
					lookup.assert_called_once_with(
						*(
							("Company", "Company", "custom_thai_withholding_tax_category")
							if party_type == "Supplier"
							else ("Customer", "Party", "customer_type")
						)
					)

	def test_fetch_wht_detail(self):
		"""Return no item WHT details when the payer is an individual."""
		# Arrange: Supply an accessible item and an individual customer.
		with (
			patch.object(frappe, "get_doc") as get_doc,
			patch.object(frappe, "get_cached_value", return_value="Individual"),
		):
			# Act and assert: Do not fall through to item or income type rates.
			self.assertEqual(
				fetch_wht_detail("ITEM", "Customer", "Party", "Company"),
				{"income_type": None, "tax_rate": 0, "source": None},
			)
			get_doc.return_value.check_permission.assert_called_once_with("read")

	def test_get_reference_withholding_tax_deductions(self):
		"""Exclude individual payers for orders and invoices in both directions."""
		for doctype, party_type, identity in (
			("Sales Order", "Customer", "Individual"),
			("Sales Invoice", "Customer", "Individual"),
			("Purchase Order", "Supplier", "Individual - Domestic"),
			("Purchase Invoice", "Supplier", "Individual - Domestic"),
		):
			with self.subTest(doctype=doctype):
				# Arrange: Enable WHT, then return the payer's individual identity.
				payment = frappe._dict(company="Company")
				reference = frappe._dict(doctype=doctype, **{frappe.scrub(party_type): "Party"})
				with patch.object(frappe, "get_cached_value", side_effect=[1, identity]):
					# Act and assert: Stop before account, category, or amount resolution.
					self.assertEqual(get_reference_withholding_tax_deductions(payment, reference), [])
