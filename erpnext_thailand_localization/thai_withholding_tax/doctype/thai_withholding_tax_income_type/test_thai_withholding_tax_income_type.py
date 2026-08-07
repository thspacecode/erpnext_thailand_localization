# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = ["Account"]


class IntegrationTestThaiWithholdingTaxIncomeType(IntegrationTestCase):
	"""
	Integration tests for ThaiWithholdingTaxIncomeType.
	Use this class for testing interactions between multiple components.
	"""

	def test_income_type_code_is_removed(self):
		meta = frappe.get_meta("Thai Withholding Tax Income Type", cached=False)
		self.assertFalse(meta.has_field("income_type_code"))

	def test_withholding_tax_account_fields_are_removed(self):
		meta = frappe.get_meta("Thai Withholding Tax Income Type", cached=False)
		self.assertFalse(meta.has_field("sales_withholding_tax_account"))
		self.assertFalse(meta.has_field("purchase_withholding_tax_account"))

	def test_rate_by_category_child_table(self):
		income_type_meta = frappe.get_meta("Thai Withholding Tax Income Type", cached=False)
		table_field = income_type_meta.get_field("thai_withholding_tax_rate_by_category")
		self.assertEqual(table_field.fieldtype, "Table")
		self.assertEqual(table_field.options, "Thai Withholding Tax Rate by Category")
		field_order = [field.fieldname for field in income_type_meta.fields]
		self.assertEqual(
			field_order.index("thai_withholding_tax_rate_by_category"),
			field_order.index("default_thai_withholding_tax_rate") + 1,
		)

		child_meta = frappe.get_meta("Thai Withholding Tax Rate by Category", cached=False)
		self.assertTrue(child_meta.istable)
		self.assertEqual(
			child_meta.get_field("thai_withholding_tax_category").options,
			"Thai Withholding Tax Category",
		)
		rate = child_meta.get_field("rate")
		self.assertEqual(rate.fieldtype, "Select")
		self.assertEqual(
			rate.options.splitlines(),
			["0", "0.5", "0.75", "1", "2", "3", "5", "10", "15"],
		)

	def test_category_pnd_child_table(self):
		income_type_meta = frappe.get_meta("Thai Withholding Tax Income Type", cached=False)
		table_field = income_type_meta.get_field("thai_withholding_tax_category_pnd")
		self.assertEqual(table_field.fieldtype, "Table")
		self.assertEqual(table_field.options, "Thai Withholding Tax Category Pnd")

		child_meta = frappe.get_meta("Thai Withholding Tax Category Pnd", cached=False)
		self.assertTrue(child_meta.istable)
		self.assertEqual(
			child_meta.get_field("thai_withholding_tax_category").options,
			"Thai Withholding Tax Category",
		)
		self.assertEqual(
			child_meta.get_field("pnd").options.splitlines(),
			["PND 1", "PND 2", "PND 3", "PND 53", "PND 54"],
		)

	def test_company_withholding_tax_fields(self):
		meta = frappe.get_meta("Company", cached=False)
		expected_fields = {
			"sales_withholding_tax_account": [
				["Account", "root_type", "=", "Asset"],
				["Account", "account_type", "=", "Tax"],
			],
			"purchase_withholding_tax_pnd3_account": [
				["Account", "root_type", "=", "Liability"],
				["Account", "account_type", "=", "Tax"],
			],
			"purchase_withholding_tax_pnd53_account": [
				["Account", "root_type", "=", "Liability"],
				["Account", "account_type", "=", "Tax"],
			],
			"purchase_withholding_tax_pnd54_account": [
				["Account", "root_type", "=", "Liability"],
				["Account", "account_type", "=", "Tax"],
			],
		}

		self.assertEqual(meta.get_field("custom_withholding_tax_tab").fieldtype, "Tab Break")
		self.assertEqual(
			meta.get_field("custom_sales_withholding_tax_section").label,
			"Sales Withholding Tax",
		)
		self.assertEqual(
			meta.get_field("custom_purchase_withholding_tax_section").label,
			"Purchase Withholding Tax",
		)
		for fieldname, filters in expected_fields.items():
			field = meta.get_field(fieldname)
			self.assertEqual(field.fieldtype, "Link")
			self.assertEqual(field.options, "Account")
			self.assertEqual(json.loads(field.link_filters), filters)
