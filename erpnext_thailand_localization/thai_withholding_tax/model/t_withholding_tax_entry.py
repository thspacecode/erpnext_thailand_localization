from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import frappe

from erpnext_thailand_localization.tests.factories import PurchaseInvoiceFactory
from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.model.withholding_tax_entry import (
		WithholdingTaxEntry,
	)


class WithholdingTaxEntryTest:
	class TestCase(ERPNextThaiTestSuite, ABC):
		@abstractmethod
		def get_base_doc(self) -> "WithholdingTaxEntry":
			"""Return a new document for the concrete entry type."""
			pass

		def test_calculate_totals(self) -> None:
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

		def test_validate_party_address(self) -> None:
			doc = self.get_base_doc()

			with self.subTest("linked address"):
				doc.validate_party_address()

			with self.subTest("unlinked address"):
				doc.set(doc.address_field, "Mr. Deckert-Billing")
				with self.assertRaisesRegex(frappe.ValidationError, "is not linked"):
					doc.validate_party_address()

		def test_validate_item(self) -> None:
			doc = self.get_base_doc()

			with self.subTest("valid item"):
				doc.validate_item(doc.items[0], "Row 1")

			with self.subTest("invalid item"):
				doc.items[0].tax_rate = 101
				with self.assertRaisesRegex(frappe.ValidationError, "no greater than 100"):
					doc.validate_item(doc.items[0], "Row 1")

		def test_validate_reference(self) -> None:
			doc = self.get_base_doc()
			reference_doc = PurchaseInvoiceFactory.create(
				supplier="Aaron Grandy",
				bill_no="TEST-WHT-REFERENCE",
				items=[
					{
						"item_code": "LEGAL-CONSULTING-SERVICE",
						"qty": 1,
						"rate": 5000,
						"price_list_rate": 5000,
					}
				],
			)
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
