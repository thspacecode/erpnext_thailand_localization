from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from erpnext_thailand_localization.doc_events.purchase_invoice import (
	convert_purchase_vat,
	get_purchase_vat_rows,
)


class TestPurchaseVatConversion(TestCase):
	def test_get_purchase_vat_rows(self):
		"""Use final THB amounts for regular invoices, discounts, and returns."""
		for base, before, after, expected_base in (
			(1000, 70, 70, 1000),
			(1000, 70, 63, 900),
			(-1000, -70, -70, -1000),
		):
			with self.subTest(base=base, after=after):
				# Arrange: ERPNext has already calculated taxes in company currency.
				doc = frappe._dict(
					base_net_total=base, supplier="Supplier", bill_no="TAX-1", bill_date="2026-01-01"
				)
				tax = frappe._dict(
					name="TAX-ROW",
					rate=7,
					charge_type="On Net Total",
					category="Total",
					add_deduct_tax="Add",
					base_tax_amount=before,
					base_tax_amount_after_discount_amount=after,
				)
				# Act and assert: Never use foreign-currency amounts or an unadjusted base.
				rows = get_purchase_vat_rows(doc, [tax])
				self.assertEqual(rows[0]["tax_base"], expected_base)
				self.assertEqual(rows[0]["tax_amount"], after)
				self.assertEqual(rows[0]["source_identity"], "TAX-ROW")

	def test_convert_purchase_vat(self):
		"""Skip missing supplier invoices and repeated conversion calls."""
		# Arrange: Simulate a locked invoice row; database persistence is covered in BMU integration.
		doc = Mock(docstatus=1, name="PI-1", bill_no="", company="Example")
		doc.taxes = [frappe._dict(account_head="Undue")]
		stored = frappe._dict(custom_purchase_vat_conversion=None)
		with (
			patch(
				"erpnext_thailand_localization.doc_events.purchase_invoice.frappe.get_doc",
				return_value=stored,
			),
			patch(
				"erpnext_thailand_localization.doc_events.purchase_invoice.frappe.get_cached_doc",
				return_value=frappe._dict(undue_purchase_value_added_tax_account="Undue"),
			),
			patch("erpnext_thailand_localization.doc_events.purchase_invoice.create_entries") as create,
		):
			# Act and assert: No supplier invoice means no recognition or ledger write.
			convert_purchase_vat(doc)
			create.assert_not_called()
			doc.db_set.assert_not_called()
			stored.custom_purchase_vat_conversion = "JE-1"
			doc.get_doc_before_save.return_value = None
			convert_purchase_vat(doc)
			create.assert_not_called()
			doc.db_set.assert_not_called()
