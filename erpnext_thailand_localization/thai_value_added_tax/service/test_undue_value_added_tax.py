from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from erpnext_thailand_localization.thai_value_added_tax.service.undue_value_added_tax import (
	fetch_undue_vat_detail,
)


class TestUndueValueAddedTax(TestCase):
	def test_fetch_undue_vat_detail(self):
		"""Resolve independent Item overrides and direct-group fallback without database writes."""
		for item_sales, item_purchase, group_sales, group_purchase, expected in (
			("", "", "", "", {"allow_sales": False, "allow_purchase": False}),
			("", "", "Allow", "Do Not Allow", {"allow_sales": True, "allow_purchase": False}),
			("", "", "Do Not Allow", "Allow", {"allow_sales": False, "allow_purchase": True}),
			(
				"Do Not Allow",
				"Do Not Allow",
				"Allow",
				"Allow",
				{"allow_sales": False, "allow_purchase": False},
			),
			("Allow", "Allow", "Do Not Allow", "Do Not Allow", {"allow_sales": True, "allow_purchase": True}),
			("Allow", "", "Do Not Allow", "Allow", {"allow_sales": True, "allow_purchase": True}),
		):
			with self.subTest(
				item_sales=item_sales,
				item_purchase=item_purchase,
				group_sales=group_sales,
				group_purchase=group_purchase,
			):
				# Arrange: Mock document reads only; this does not test Frappe permissions.
				item = Mock()
				item.item_group = "Services"
				item.get.side_effect = {
					"custom_allow_undue_sales_value_added_tax": item_sales,
					"custom_allow_undue_purchase_value_added_tax": item_purchase,
				}.get
				group = frappe._dict(
					custom_allow_undue_sales_value_added_tax=group_sales,
					custom_allow_undue_purchase_value_added_tax=group_purchase,
				)
				with (
					patch.object(frappe, "get_doc", return_value=item),
					patch.object(frappe, "get_cached_doc", return_value=group) as get_group,
				):
					# Act and assert: Each explicit value overrides only its own direction.
					self.assertEqual(fetch_undue_vat_detail("SERVICE"), expected)
					item.check_permission.assert_called_once_with("read")
					get_group.assert_called_once_with("Item Group", "Services")
