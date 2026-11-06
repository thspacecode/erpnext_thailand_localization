from unittest import TestCase
from unittest.mock import patch

import frappe

from erpnext_thailand_localization.doc_events.invoice import validate_undue_vat_items


def raise_validation_error(message):
	"""Raise the real error type without Frappe's request message handling."""
	raise frappe.ValidationError(message)


class TestInvoiceUndueVat(TestCase):
	def test_validate_undue_vat_items(self):
		"""Check both directions, all rows, template detection, and direct-account detection."""
		for doctype, direction in (("Sales Invoice", "sales"), ("Purchase Invoice", "purchase")):
			with self.subTest(doctype=doctype):
				# Arrange: Mock Company lookup and eligibility; resolver has separate tests.
				company = frappe._dict(
					{
						f"custom_undue_{direction}_value_added_tax_templates": [
							frappe._dict(tax_template="Thai Undue VAT")
						],
						f"undue_{direction}_value_added_tax_account": "Undue VAT",
					}
				)
				doc = frappe._dict(
					doctype=doctype,
					company="Example",
					taxes_and_charges="Thai Undue VAT",
					taxes=[],
					items=[frappe._dict(idx=1, item_code="SERVICE"), frappe._dict(idx=2, item_code="PAPER")],
				)
				allowed = {"allow_sales": True, "allow_purchase": True}
				disallowed = {"allow_sales": True, "allow_purchase": True, f"allow_{direction}": False}
				with (
					patch(
						"erpnext_thailand_localization.doc_events.invoice.frappe.get_cached_doc",
						return_value=company,
					),
					patch(
						"erpnext_thailand_localization.doc_events.invoice.fetch_undue_vat_detail"
					) as resolve,
					patch(
						"erpnext_thailand_localization.doc_events.invoice.frappe.throw",
						side_effect=raise_validation_error,
					),
				):
					# Act and assert: A valid invoice passes and every row is checked.
					resolve.return_value = allowed
					validate_undue_vat_items(doc)
					self.assertEqual(resolve.call_count, 2)
					resolve.reset_mock()
					resolve.side_effect = [allowed, disallowed]
					with self.assertRaisesRegex(
						frappe.ValidationError, f"Row 2: Item PAPER does not allow undue {direction} VAT"
					):
						validate_undue_vat_items(doc)

					# Regular templates must not impose undue VAT restrictions.
					doc.taxes_and_charges = "Regular VAT"
					resolve.reset_mock(side_effect=True)
					validate_undue_vat_items(doc)
					resolve.assert_not_called()

					# A direct undue-account row still requires eligible Items.
					doc.taxes = [frappe._dict(account_head="Undue VAT")]
					resolve.return_value = disallowed
					with self.assertRaisesRegex(
						frappe.ValidationError, f"Row 1: Item SERVICE does not allow undue {direction} VAT"
					):
						validate_undue_vat_items(doc)

					# A free-text row cannot bypass the eligibility check.
					doc.items = [frappe._dict(idx=1, item_code=None)]
					with self.assertRaisesRegex(frappe.ValidationError, "Row 1: Select an Item"):
						validate_undue_vat_items(doc)
