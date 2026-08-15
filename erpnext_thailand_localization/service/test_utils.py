import frappe

from erpnext_thailand_localization.service.utils import (
	normalize_branch_code,
	normalize_digits,
	validate_branch_code,
	validate_tax_id,
)
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite


class TestUtils(ERPNextThaiTestSuite):
	def test_normalize_digits(self) -> None:
		with self.subTest("removes non-digit characters"):
			self.assertEqual(normalize_digits("1-234-567 890"), "1234567890")

		with self.subTest("returns an empty string for a missing value"):
			self.assertEqual(normalize_digits(None), "")

	def test_normalize_branch_code(self) -> None:
		with self.subTest("pads a short branch code with zeroes"):
			self.assertEqual(normalize_branch_code("123"), "00123")

		with self.subTest("returns the head office code for a missing value"):
			self.assertEqual(normalize_branch_code(None), "00000")

	def test_validate_tax_id(self) -> None:
		with self.subTest("accepts a valid value"):
			self.assertIsNone(validate_tax_id("1-2345-67890-12-3", "Tax ID"))

		with self.subTest("raises an error for an invalid value"):
			with self.assertRaisesRegex(frappe.ValidationError, "Tax ID must contain exactly 13 digits"):
				validate_tax_id("123", "Tax ID")

	def test_validate_branch_code(self) -> None:
		with self.subTest("accepts a valid value"):
			self.assertIsNone(validate_branch_code("00123", "Branch Code"))

		with self.subTest("raises an error for an invalid value"):
			with self.assertRaisesRegex(frappe.ValidationError, "Branch Code must contain exactly 5 digits"):
				validate_branch_code("123", "Branch Code")
