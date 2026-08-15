from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import frappe

from erpnext_thailand_localization.tests.factories import (
	CompanyAddressFactory,
	PurchaseWithholdingTaxEntryFactory,
)
from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite

if TYPE_CHECKING:
	from frappe.contacts.doctype.address.address import Address

	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling


class PNDFilingTest:
	class TestCase(ERPNextThaiTestSuite, ABC):
		@abstractmethod
		def get_base_doc(self) -> "PNDFiling":
			"""Return a new document for the concrete PND filing type."""
			pass

		def create_company_address(self) -> "Address":
			pnd_type = self.get_base_doc().pnd_type
			return CompanyAddressFactory.create(address_title=f"Dunder Mifflin {pnd_type} Test")

		def get_supplier(self, opposite_pnd: bool = False) -> tuple[str, str]:
			use_individual = (self.get_base_doc().pnd_type == "PND 3") != opposite_pnd
			if use_individual:
				return "Aaron Grandy", "Aaron Grandy-Billing"
			return "Hammermill Paper Company", "Hammermill Paper Company-Billing"

		def create_source(
			self, submit: bool = False, opposite_pnd: bool = False
		) -> "PurchaseWithholdingTaxEntry":
			supplier, supplier_address = self.get_supplier(opposite_pnd=opposite_pnd)
			return PurchaseWithholdingTaxEntryFactory.create(
				supplier=supplier,
				supplier_address=supplier_address,
				submit=submit,
			)

		def get_filing_for_source(self, source: "PurchaseWithholdingTaxEntry") -> "PNDFiling":
			doc = self.get_base_doc()
			doc.update(
				{
					"company": "Dunder Mifflin",
					"tax_period": "2026-08-01",
					"filing_type": "Normal",
					"legal_basis": doc.legal_bases[0],
				}
			)
			doc.append(
				"items",
				{
					"purchase_withholding_tax_entry": source.name,
					"withholding_tax_entry_item": source.items[0].name,
				},
			)
			return doc

		def get_valid_filing(self, submit_source: bool = False) -> "PNDFiling":
			source = self.create_source(submit=submit_source)
			doc = self.get_filing_for_source(source)
			doc.company_address = self.create_company_address().name
			return doc

		def test_normalize_period(self) -> None:
			doc = self.get_base_doc()
			doc.tax_period = "2026-08-19"

			doc.normalize_period()

			self.assertEqual(str(doc.tax_period), "2026-08-01")

		def test_calculate_totals(self) -> None:
			doc = self.get_base_doc()
			doc.surcharge_amount = 5
			doc.set(
				"items",
				[
					{
						"recipient_tax_id": "1103700000001",
						"recipient_branch_code": "00000",
						"base_amount": 1000,
						"tax_amount": 30,
					},
					{
						"recipient_tax_id": "1103700000001",
						"recipient_branch_code": "00000",
						"base_amount": 500,
						"tax_amount": 15,
					},
				],
			)

			doc.calculate_totals()

			self.assertEqual(doc.recipient_count, 1)
			self.assertEqual(doc.attachment_page_count, 1)
			self.assertEqual(doc.total_base_amount, 1500)
			self.assertEqual(doc.total_tax_amount, 45)
			self.assertEqual(doc.grand_total, 50)

		def test_validate(self) -> None:
			doc = self.get_valid_filing()

			doc.validate()

			self.assertEqual(str(doc.tax_period), "2026-08-01")
			self.assertEqual(doc.company_name, "Dunder Mifflin")
			self.assertEqual(doc.company_tax_id, "0105555000001")
			self.assertEqual(doc.items[0].base_amount, 1000)
			self.assertEqual(doc.total_tax_amount, 30)

		def test_before_submit(self) -> None:
			doc = self.get_valid_filing(submit_source=True)
			doc.validate()

			doc.before_submit()

		def test_validate_filing_details(self) -> None:
			doc = self.get_base_doc()
			doc.legal_basis = doc.legal_bases[0]
			doc.filing_type = "Normal"
			doc.additional_filing_no = 2

			with self.subTest("normal filing resets the additional filing number"):
				doc.validate_filing_details()
				self.assertEqual(doc.additional_filing_no, 0)

			with self.subTest("invalid legal basis"):
				doc.legal_basis = "Invalid"
				with self.assertRaisesRegex(frappe.ValidationError, "Legal Basis"):
					doc.validate_filing_details()

			with self.subTest("invalid additional filing number"):
				doc.legal_basis = doc.legal_bases[0]
				doc.filing_type = "Additional"
				doc.additional_filing_no = 0
				with self.assertRaisesRegex(frappe.ValidationError, "must be greater than zero"):
					doc.validate_filing_details()

			with self.subTest("duplicate filing"):
				existing = self.get_base_doc()
				existing.update(
					{
						"company": "Dunder Mifflin",
						"tax_period": "2026-08-01",
						"filing_type": "Additional",
						"additional_filing_no": 1,
					}
				)
				existing.db_insert()

				doc.company = existing.company
				doc.tax_period = existing.tax_period
				doc.additional_filing_no = existing.additional_filing_no
				with self.assertRaisesRegex(frappe.ValidationError, "filing already exists"):
					doc.validate_filing_details()

		def test_set_company_snapshot(self) -> None:
			doc = self.get_base_doc()
			doc.company = "Dunder Mifflin"
			doc.company_address = self.create_company_address().name

			doc.set_company_snapshot()

			self.assertEqual(doc.company_name, "Dunder Mifflin")
			self.assertEqual(doc.company_currency, "THB")
			self.assertEqual(doc.company_tax_id, "0105555000001")
			self.assertEqual(doc.company_branch_code, "00000")
			self.assertEqual(doc.company_address_line1, "1725 Slough Avenue")
			self.assertEqual(doc.company_province, "Bangkok")

		def test_set_item_snapshots(self) -> None:
			source = self.create_source()
			doc = self.get_filing_for_source(source)

			doc.set_item_snapshots()

			item = doc.items[0]
			self.assertEqual(str(item.payment_date), source.payment_date)
			self.assertEqual(item.supplier, source.supplier)
			self.assertEqual(
				item.recipient_name, frappe.db.get_value("Supplier", source.supplier, "supplier_name")
			)
			self.assertEqual(
				item.recipient_tax_id, frappe.db.get_value("Supplier", source.supplier, "tax_id")
			)
			self.assertEqual(item.recipient_branch_code, "00000")
			self.assertEqual(item.income_type, source.items[0].income_type)
			self.assertEqual(item.base_amount, 1000)
			self.assertEqual(item.tax_amount, 30)
			self.assertEqual(item.address_line1, "123 Paper Street")
			if doc.pnd_type == "PND 3":
				self.assertEqual(item.recipient_first_name, "Aaron")
				self.assertEqual(item.recipient_last_name, "Grandy")

		def test_validate_required_tax_data(self) -> None:
			doc = self.get_base_doc()
			doc.company_tax_id = "1234567890123"
			doc.company_branch_code = "00000"
			doc.set(
				"items",
				[
					{
						"recipient_tax_id": "1234567890123",
						"recipient_branch_code": "00000",
						"base_amount": 1000,
						"tax_rate": 3,
						"tax_amount": 30,
					}
				],
			)

			with self.subTest("valid tax data"):
				doc.validate_required_tax_data()

			with self.subTest("missing items"):
				doc.set("items", [])
				with self.assertRaisesRegex(frappe.ValidationError, "At least one"):
					doc.validate_required_tax_data()

			with self.subTest("invalid amounts"):
				doc.set(
					"items",
					[
						{
							"recipient_tax_id": "1234567890123",
							"recipient_branch_code": "00000",
							"base_amount": 0,
							"tax_rate": 3,
							"tax_amount": 30,
						}
					],
				)
				with self.assertRaisesRegex(frappe.ValidationError, "must be greater than zero"):
					doc.validate_required_tax_data()

			with self.subTest("invalid rate"):
				doc.items[0].base_amount = 1000
				doc.items[0].tax_rate = 101
				with self.assertRaisesRegex(frappe.ValidationError, "no greater than 100"):
					doc.validate_required_tax_data()

		def test_validate_sources(self) -> None:
			source = self.create_source(submit=True)
			doc = self.get_filing_for_source(source)

			with self.subTest("submitted source"):
				doc.validate_sources()

			with self.subTest("unsubmitted source"):
				draft_source = self.create_source()
				draft_doc = self.get_filing_for_source(draft_source)
				with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
					draft_doc.validate_sources()

			with self.subTest("wrong PND mapping"):
				wrong_source = self.create_source(submit=True, opposite_pnd=True)
				wrong_doc = self.get_filing_for_source(wrong_source)
				with self.assertRaisesRegex(frappe.ValidationError, "Income Type"):
					wrong_doc.validate_sources()

		def test_validate_duplicate_sources(self) -> None:
			doc = self.get_base_doc()
			doc.set(
				"items",
				[
					{"withholding_tax_entry_item": "PWHT-ITEM-1"},
					{"withholding_tax_entry_item": "PWHT-ITEM-1"},
				],
			)

			with self.subTest("duplicate source in the current filing"):
				with self.assertRaisesRegex(frappe.ValidationError, "cannot be included more than once"):
					doc.validate_duplicate_sources()

			with self.subTest("unique source not included in another filing"):
				doc.set("items", [{"withholding_tax_entry_item": "PWHT-ITEM-2"}])
				doc.validate_duplicate_sources()

			with self.subTest("source already included in a submitted filing"):
				frappe.get_doc(
					{
						"doctype": doc.item_doctype,
						"parent": "PND-DUPLICATE",
						"parenttype": doc.doctype,
						"parentfield": "items",
						"docstatus": 1,
						"withholding_tax_entry_item": "PWHT-ITEM-2",
					}
				).db_insert()
				with self.assertRaisesRegex(frappe.ValidationError, "already filed"):
					doc.validate_duplicate_sources()

		def test_validate_linked_address(self) -> None:
			address = self.create_company_address()
			doc = self.get_base_doc()

			with self.subTest("linked address"):
				doc.validate_linked_address("Company", "Dunder Mifflin", address.name)

			with self.subTest("unlinked address"):
				with self.assertRaisesRegex(frappe.ValidationError, "is not linked"):
					doc.validate_linked_address(
						"Company", "Dunder Mifflin", "Hammermill Paper Company-Billing"
					)
