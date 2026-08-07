from abc import ABC, abstractmethod

import frappe
from frappe.model.document import Document

from erpnext_thailand_localization.data.test_data.bootstrap_test_data import BaseTestRecord
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite


class WithholdingTaxEntryTest:
	class TestCase(ERPNextThaiTestSuite, ABC):
		@abstractmethod
		def get_base_doc(self) -> Document:
			"""Return a new document for the concrete entry type."""
			raise NotImplementedError

		def test_calculate_totals(self):
			doc = self.get_base_doc()
			doc.set(
				"items",
				[
					{"base_amount": 1000, "tax_rate": 3, "tax_amount": 999},
					{"base_amount": 250.55, "tax_rate": 0.5, "tax_amount": 999},
				],
			)

			doc.calculate_totals()

			self.assertEqual(doc.items[0].tax_amount, 30)
			self.assertEqual(doc.items[1].tax_amount, 1.25)
			self.assertEqual(doc.total_base_amount, 1250.55)
			self.assertEqual(doc.total_tax_amount, 31.25)

		def test_validate_party_address(self):
			doc = self.get_base_doc()

			with self.subTest("linked address"):
				doc.validate_party_address()

			with self.subTest("unlinked address"):
				doc.set(doc.address_field, "Mr. Deckert-Billing")
				with self.assertRaisesRegex(frappe.ValidationError, "is not linked"):
					doc.validate_party_address()

		def test_validate_item(self):
			doc = self.get_base_doc()

			with self.subTest("valid item"):
				doc.validate_item(doc.items[0], "Row 1")

			with self.subTest("invalid item"):
				doc.items[0].tax_rate = 101
				with self.assertRaisesRegex(frappe.ValidationError, "no greater than 100"):
					doc.validate_item(doc.items[0], "Row 1")

		def test_validate_reference(self):
			doc = self.get_base_doc()
			reference_doc = frappe.get_doc(
				BaseTestRecord.purchase_invoice(
					supplier="Aaron Grandy",
					supplier_invoice_no="TEST-WHT-REFERENCE",
					items=[("LEGAL-CONSULTING-SERVICE", 5000)],
				)
			)
			reference_doc.set_missing_values()
			reference_doc.insert()
			reference_item = reference_doc.items[0]
			doc.items[0].update(
				{
					"reference_doc_doctype": reference_doc.doctype,
					"reference_doc": reference_doc.name,
					"reference_doc_item_doctype": reference_item.doctype,
					"reference_doc_item": reference_item.name,
				}
			)

			with self.subTest("matching reference item"):
				doc.validate_reference(doc.items[0], "Row 1")

			with self.subTest("mismatched reference item"):
				doc.items[0].reference_doc = f"{reference_doc.name}-OTHER"
				with self.assertRaisesRegex(frappe.ValidationError, "does not belong"):
					doc.validate_reference(doc.items[0], "Row 1")
