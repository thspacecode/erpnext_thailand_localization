from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from erpnext_thailand_localization.thai_value_added_tax.service.undue_value_added_tax import (
	fetch_undue_vat_detail,
)


class TestUndueValueAddedTax(TestCase):
	def test_fetch_undue_vat_detail(self):
		"""Keep sales Item overrides and direct-group fallback without database writes."""
		for item_sales, group_sales, expected in (
			("", "", False),
			("", "Allow", True),
			("", "Do Not Allow", False),
			("Do Not Allow", "Allow", False),
			("Allow", "Do Not Allow", True),
		):
			with self.subTest(item_sales=item_sales, group_sales=group_sales):
				# Arrange: Mock reads only; this does not test Frappe permissions.
				item = Mock(item_group="Services")
				item.get.return_value = item_sales
				group = frappe._dict(custom_allow_undue_sales_value_added_tax=group_sales)
				with (
					patch.object(frappe, "get_doc", return_value=item),
					patch.object(frappe, "get_cached_doc", return_value=group),
				):
					# Act and assert: Only sales eligibility remains in the result.
					self.assertEqual(fetch_undue_vat_detail("SERVICE"), {"allow_sales": expected})
					item.check_permission.assert_called_once_with("read")
					item.get.assert_called_once_with("custom_allow_undue_sales_value_added_tax")
