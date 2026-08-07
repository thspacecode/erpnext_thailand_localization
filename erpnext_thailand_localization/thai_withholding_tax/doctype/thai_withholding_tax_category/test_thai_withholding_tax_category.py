# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class IntegrationTestThaiWithholdingTaxCategory(IntegrationTestCase):
	def test_initial_categories_exist(self):
		expected_categories = {
			"Individual - Domestic",
			"Juristic Person - Domestic",
			"Foundation or Association",
			"Individual - Foreign",
			"Government or Tax-Exempt Entity",
		}

		self.assertTrue(
			expected_categories.issubset(set(frappe.get_all("Thai Withholding Tax Category", pluck="name")))
		)

	def test_category_links_are_positioned_on_party_doctypes(self):
		expected_positions = {
			"Customer": ("tax_withholding_group", "before"),
			"Supplier": ("tax_withholding_category", "before"),
			"Company": ("tax_id", "after"),
		}

		for doctype, (adjacent_fieldname, position) in expected_positions.items():
			meta = frappe.get_meta(doctype, cached=False)
			field = meta.get_field("custom_thai_withholding_tax_category")
			self.assertIsNotNone(field)
			self.assertEqual(field.fieldtype, "Link")
			self.assertEqual(field.options, "Thai Withholding Tax Category")

			field_order = [meta_field.fieldname for meta_field in meta.fields]
			field_index = field_order.index(field.fieldname)
			adjacent_index = field_order.index(adjacent_fieldname)
			if position == "before":
				self.assertEqual(field_index + 1, adjacent_index)
			else:
				self.assertEqual(adjacent_index + 1, field_index)
