from unittest import TestCase

import frappe

from erpnext_thailand_localization.thai_value_added_tax.service.purchase_vat import (
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
					account_head="Undue",
					rate=7,
					charge_type="On Net Total",
					category="Total",
					add_deduct_tax="Add",
					base_tax_amount=before,
					base_tax_amount_after_discount_amount=after,
				)
				# Act and assert: Never use foreign-currency amounts or an unadjusted base.
				rows = get_purchase_vat_rows(
					doc,
					[tax],
					tax_invoice_number="TAX-1",
					tax_invoice_date="2026-01-01",
					report_date="2026-01-01",
				)
				self.assertEqual(rows[0]["tax_base"], expected_base)
				self.assertEqual(rows[0]["tax_amount"], after)
				self.assertEqual(rows[0]["source_identity"], "TAX-ROW")
