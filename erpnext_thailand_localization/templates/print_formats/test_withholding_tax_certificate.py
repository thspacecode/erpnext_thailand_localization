import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from erpnext_thailand_localization.templates.print_formats.withholding_tax_certificate import (
	certificate_rows,
	purchase_withholding_certificate,
)


class TestCertificateRows(unittest.TestCase):
	def test_certificate_rows(self):
		"""Group service income and preserve decimal tax totals."""
		items = [
			frappe._dict(income_type="5 ค่าเช่า", base_amount=100.1, tax_amount=3.01),
			frappe._dict(income_type="8 อื่นๆ", base_amount=200.2, tax_amount=6.01),
			frappe._dict(income_type="1 เงินเดือน", base_amount=1000, tax_amount=10),
		]
		rows = certificate_rows(items)
		self.assertEqual(rows["services"].base, Decimal("300.3"))
		self.assertEqual(rows["services"].tax, Decimal("9.02"))
		self.assertEqual(rows["1"].base, Decimal("1000"))
		self.assertEqual(len(rows["services"].descriptions), 2)

	def test_certificate_rows_income_sections(self):
		"""Keep interest and other income separate from service income."""
		items = [
			frappe._dict(income_type="4 ก ดอกเบี้ย", base_amount=1000.25, tax_amount=150.04),
			frappe._dict(income_type="4 อื่นๆ", base_amount=2000.50, tax_amount=200.05),
		]
		rows = certificate_rows(items)
		self.assertEqual(set(rows), {"interest", "other"})
		self.assertEqual(rows["interest"].tax, Decimal("150.04"))
		self.assertEqual(rows["other"].descriptions, ["4 อื่นๆ"])


class TestPurchaseWithholdingCertificate(unittest.TestCase):
	def test_purchase_withholding_certificate(self):
		"""Use the company as payer and the supplier as recipient for each purchase PND."""
		# Arrange: Mock master lookups only. No customer data belongs to this certificate.
		masters = {
			("Company", "Company"): frappe._dict(company_name="Payer", tax_id="0-123456789012"),
			("Supplier", "Supplier"): frappe._dict(supplier_name="Recipient", tax_id="9-876543210987"),
			("Address", "Company Address"): frappe._dict(address_line1="Company road", city="Bangkok"),
			("Address", "Supplier Address"): frappe._dict(address_line1="Supplier road", city="Bangkok"),
		}
		doc = SimpleNamespace(
			company="Company",
			supplier="Supplier",
			supplier_address="Supplier Address",
			payment_date="2026-11-11",
			pnd="PND 53",
			total_tax_amount=300,
		)
		doc.items = [frappe._dict(income_type="8 บริการ", base_amount=10000, tax_amount=300)]
		with (
			patch.object(frappe, "get_doc", side_effect=lambda doctype, name: masters[(doctype, name)]),
			patch.object(frappe, "get_all", side_effect=[["Company Address"], ["Company Address"]]),
		):
			# Act: Read the real helper with controlled master data.
			certificate = purchase_withholding_certificate(doc)

		# Assert: Purchase parties must not be reversed as on a sales entry.
		self.assertEqual(certificate.payer, "Payer")
		self.assertEqual(certificate.payer_tax_id, "0123456789012")
		self.assertEqual(certificate.payer_address, "Company road Bangkok")
		self.assertEqual(certificate.recipient, "Recipient")
		self.assertEqual(certificate.recipient_tax_id, "9876543210987")
		self.assertEqual(certificate.recipient_address, "Supplier road Bangkok")
		self.assertEqual(certificate.pnd_types, {"PND 53"})
		self.assertEqual(certificate.date, "11/11/2569")
		self.assertEqual(certificate.rows["services"].tax, Decimal("300"))

		# Arrange: Missing optional data must not introduce a company-category PND.
		doc.pnd = "PND 3"
		doc.payment_date = None
		doc.supplier_address = None
		with (
			patch.object(frappe, "get_doc", side_effect=lambda doctype, name: masters[(doctype, name)]),
			patch.object(frappe, "get_all", return_value=[]),
		):
			certificate = purchase_withholding_certificate(doc)
		self.assertEqual(certificate.pnd_types, {"PND 3"})
		self.assertEqual(certificate.payer_address, "")
		self.assertEqual(certificate.recipient_address, "")
		self.assertEqual(certificate.date, "")
