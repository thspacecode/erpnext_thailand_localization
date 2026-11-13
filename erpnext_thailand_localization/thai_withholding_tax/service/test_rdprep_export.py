"""Cover RDPrep serialization and download controls without claiming Windows compatibility."""

from unittest.mock import patch

import frappe

from erpnext_thailand_localization.tests.factories import ThaiPND3FilingFactory, ThaiPND53FilingFactory
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.service.rdprep_export import (
	build_rdprep_text,
	download_rdprep,
	rdprep_condition,
	rdprep_decimal,
	rdprep_text,
	validate_rdprep_tax_id,
)


class TestRDPrepExport(ERPNextThaiTestSuite):
	def build_filing(self, pnd53=False):
		"""Build unsaved synthetic snapshots; no linked masters are inserted."""
		doc = (ThaiPND53FilingFactory if pnd53 else ThaiPND3FilingFactory).build(
			company_tax_id="0105550000015", tax_period="2020-01-01", filing_type="Normal"
		)
		doc.docstatus = 1
		doc.append(
			"items",
			{
				"recipient_tax_id": "0105550000023" if pnd53 else "1101700207030",
				"recipient_branch_code": "00001",
				"recipient_title": "นาย",
				"recipient_first_name": "สมชาย",
				"recipient_last_name": "ใจดี",
				"recipient_name": "บริษัท ทดสอบ จำกัด",
				"payment_date": "2020-01-15",
				"income_description": "ค่าบริการ",
				"base_amount": 1000,
				"tax_amount": 30,
				"tax_rate": 3,
				"tax_payment_condition": "Withheld",
				"subdistrict": "บางรัก",
				"district": "บางรัก",
				"province": "กรุงเทพมหานคร",
				"postal_code": "10500",
				"address_line1": "12/3 อาคาร ทดสอบ",
				"address_line2": "ถนน สีลม",
			},
		)
		return doc

	def test_build_rdprep_text(self):
		"""Serialize both forms, repeated recipients, and reference-only addresses."""
		for pnd53 in (False, True):
			with self.subTest(pnd53=pnd53):
				# Arrange: Two income items may refer to the same recipient.
				doc = self.build_filing(pnd53)
				doc.append("items", doc.items[0].as_dict())
				# Act: No grouping or address parsing occurs during export.
				text = build_rdprep_text(doc)
				rows = [line.split("|") for line in text.splitlines()]
				# Assert: Output preserves Thai text, zeros, amounts, and trailing columns.
				self.assertEqual(len(rows), 3)
				self.assertEqual([row[0] for row in rows[1:]], ["1", "2"])
				self.assertEqual(len(rows[0]), 19)
				self.assertEqual(rows[1][2], "00001")
				self.assertEqual(rows[1][4], "บริษัท ทดสอบ จำกัด" if pnd53 else "สมชาย")
				self.assertEqual(
					rows[1][11:17], ["2020-01-15", "ค่าบริการ", "3", "1000.00", "30.00", "1" if pnd53 else "0"]
				)
				self.assertEqual(rows[1][-2:], ["12/3 อาคาร ทดสอบ", "ถนน สีลม"])
				self.assertNotIn("houseNo", rows[0])
				self.assertTrue(text.endswith("\r\n"))
				self.assertEqual(text.count("\n"), text.count("\r\n"))

	def test_export_validation(self):
		"""Reject export-specific invalid data after a valid baseline."""
		self.assertTrue(build_rdprep_text(self.build_filing()))
		for field, value, message in (
			("tax_rate", 36, "at most 35"),
			("tax_amount", 31, "more than 0.99"),
			("base_amount", 1000.001, "two decimal places"),
			("payment_date", "2020-02-01", "match the filing period"),
			("payment_date", "2099-01-01", "cannot be in the future"),
			("postal_code", "AB123", "Postcode"),
			("recipient_branch_code", "1", "five digits"),
			("recipient_title", "", "titleName is required"),
			("recipient_first_name", 'Bad"Name', "characters"),
			("income_description", "x" * 201, "exceeds 200"),
			("address_line1", "First\nSecond", "characters"),
			("recipient_tax_id", "0105550000015", "must differ"),
			("tax_payment_condition", "Other", "Unsupported tax payment condition"),
		):
			with self.subTest(field=field, value=value):
				# Arrange: Change one field in a fresh valid snapshot.
				doc = self.build_filing()
				doc.items[0].set(field, value)
				# Act and assert: Error identifies the output row.
				with self.assertRaisesRegex(frappe.ValidationError, "Row 1:.*" + message):
					build_rdprep_text(doc)

	def test_rdprep_condition(self):
		"""Keep input codes separate from internal keys for all semantic values."""
		for form, condition, code in (
			("PND 3", "Withheld", "0"),
			("PND 3", "Payer Bears Tax Continuously", "1"),
			("PND 3", "Payer Bears Tax One Time", "2"),
			("PND 53", "Withheld", "1"),
			("PND 53", "Payer Bears Tax Continuously", "2"),
			("PND 53", "Payer Bears Tax One Time", "2"),
		):
			with self.subTest(form=form, condition=condition):
				# Act and assert: Use the defaults from RDPrep's bundled status tables.
				self.assertEqual(rdprep_condition(form, condition, "Row 1"), code)

	def test_validate_rdprep_tax_id(self):
		"""Reject wrong checksums and checksum-valid dummy tax IDs."""
		# Arrange and assert: Synthetic non-dummy IDs pass checksum validation only.
		validate_rdprep_tax_id("0105550000015", "Company")
		for value in ("0105550000014", "1111111111119", "abc"):
			with self.subTest(value=value):
				with self.assertRaisesRegex(frappe.ValidationError, "Invalid RDPrep Tax ID"):
					validate_rdprep_tax_id(value, "Company")

	def test_rdprep_decimal(self):
		"""Reject non-finite and oversized amounts without a decimal runtime error."""
		for value in (None, "NaN", "Infinity", "1e100", "0.001"):
			with self.subTest(value=value):
				with self.assertRaisesRegex(
					frappe.ValidationError, "Invalid RDPrep number|RDPrep amounts require"
				):
					rdprep_decimal(value, "Row 1")

	def test_rdprep_text(self):
		"""Forbid separators and mapped special characters, but retain reference punctuation."""
		# Act and assert: Unmapped reference columns can retain original punctuation.
		self.assertEqual(
			rdprep_text('O\'Brien "Building"', "Row 1", "reference", 0, reference=True), 'O\'Brien "Building"'
		)
		for value in ("a|b", "a\nb", "a\rb", "a\x00b", "O'Brien", "a?b"):
			with self.subTest(value=value):
				with self.assertRaisesRegex(frappe.ValidationError, "contains characters"):
					rdprep_text(value, "Row 1", "name", 100)

	def test_download_rdprep(self):
		"""Check permission and submitted status; verify BOM bytes with a mocked document lookup."""
		doc = self.build_filing()
		module = "erpnext_thailand_localization.thai_withholding_tax.service.rdprep_export"
		# Arrange: Mock lookup, not serialization. This does not prove HTTP routing or real permissions.
		with (
			patch(module + ".frappe.get_doc", return_value=doc),
			patch.object(doc, "check_permission") as permission,
		):
			download_rdprep(doc.doctype, "TEST-FILING")
			permission.assert_called_once_with("read")
			self.assertTrue(frappe.response.filecontent.startswith(b"\xef\xbb\xbf"))
			self.assertEqual(frappe.response.filename, "PND3-2020-01.txt")
			doc.docstatus = 0
			with self.assertRaisesRegex(frappe.ValidationError, "Submit the filing"):
				download_rdprep(doc.doctype, "TEST-FILING")
		with self.assertRaisesRegex(frappe.ValidationError, "Unsupported PND filing type"):
			download_rdprep("Supplier", "TEST")

	def test_build_rdprep_row(self):
		"""Check amount tolerance boundaries and form-specific recipient IDs."""
		# Arrange: RDPrep accepts differences up to 0.99 for slot one.
		doc = self.build_filing()
		doc.items[0].tax_amount = 30.99
		self.assertIn("30.99", build_rdprep_text(doc))
		doc.items[0].tax_amount = 29.01
		self.assertIn("29.01", build_rdprep_text(doc))
		# Act and assert: PND53 must not accept an individual recipient.
		doc = self.build_filing(True)
		doc.items[0].recipient_tax_id = "1101700207030"
		with self.assertRaisesRegex(frappe.ValidationError, "Row 1:.*not valid for PND53"):
			build_rdprep_text(doc)
		# Arrange: Use a checksum-valid disallowed 0993 ID in PND3.
		doc = self.build_filing()
		doc.items[0].recipient_tax_id = "0993000000013"
		with self.assertRaisesRegex(frappe.ValidationError, "Row 1:.*not valid for PND3"):
			build_rdprep_text(doc)

	def test_filing_limits(self):
		"""Reject an empty export and preserve normal versus additional amount rules."""
		doc = self.build_filing()
		doc.items = []
		with self.assertRaisesRegex(frappe.ValidationError, "between 1 and 99999"):
			build_rdprep_text(doc)
		# Arrange: A small tax-only adjustment can pass RDPrep's additional filing rules.
		doc = self.build_filing()
		doc.items[0].base_amount = 0
		doc.items[0].tax_amount = 0.50
		with self.assertRaisesRegex(frappe.ValidationError, "not valid for this filing type"):
			build_rdprep_text(doc)
		doc.filing_type = "Additional"
		self.assertIn("|0.00|0.50|", build_rdprep_text(doc))

	def test_download_permission(self):
		"""Stop a denied lookup before returning any export content."""
		doc = self.build_filing()
		module = "erpnext_thailand_localization.thai_withholding_tax.service.rdprep_export"
		# Arrange: Simulate permission denial; this does not test the permission engine.
		with (
			patch(module + ".frappe.get_doc", return_value=doc),
			patch.object(doc, "check_permission", side_effect=frappe.PermissionError),
			patch(module + ".build_rdprep_text") as build,
		):
			with self.assertRaisesRegex(frappe.PermissionError, "^$"):
				download_rdprep(doc.doctype, "TEST-FILING")
			build.assert_not_called()
