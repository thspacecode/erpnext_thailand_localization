import frappe

from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.address import validate_address


class TestAddress(ERPNextThaiTestSuite):
	def test_normalizes_branch_code(self) -> None:
		address = frappe.new_doc("Address")
		address.set("branch_code", "123")

		validate_address(address)

		self.assertEqual(address.get("branch_code"), "00123")

	def test_defaults_branch_code_to_head_office(self) -> None:
		address = frappe.new_doc("Address")

		validate_address(address)

		self.assertEqual(address.get("branch_code"), "00000")

	def test_rejects_branch_codes_longer_than_five_digits(self) -> None:
		address = frappe.new_doc("Address")
		address.set("branch_code", "123456")

		with self.assertRaisesRegex(frappe.ValidationError, "Branch Code must contain exactly 5 digits"):
			validate_address(address)
