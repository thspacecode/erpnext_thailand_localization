import frappe

from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	apply_thai_withholding_tax,
	fetch_wht_detail,
)


class TestWithholdingTax(ERPNextThaiTestSuite):
	def test_fetch_wht_detail(self):
		self.assertEqual(
			fetch_wht_detail(
				"WAREHOUSE-RENT",
				party_type="Customer",
				party="Vance Refrigeration",
				company="Dunder Mifflin",
			),
			{"income_type": "5 ค่าเช่า", "tax_rate": 5.0, "source": "Item"},
		)

	def test_applies_thai_withholding_tax_to_invoice_payment_entries(self):
		for invoice, expected_amount, expected_account in (
			(
				self.make_invoice(
					"Sales Invoice",
					"Customer",
					"Vance Refrigeration",
					"WAREHOUSE-RENT",
					12000,
				),
				600,
				"Sales Withholding Tax Receivable - DM",
			),
			(
				self.make_invoice(
					"Purchase Invoice",
					"Supplier",
					"Aaron Grandy",
					"LEGAL-CONSULTING-SERVICE",
					5000,
				),
				-150,
				"Purchase Withholding Tax PND 3 Payable - DM",
			),
		):
			payment_entry = self.make_invoice_payment_entry(invoice)

			apply_thai_withholding_tax(payment_entry, invoice)

			self.assertEqual(payment_entry.deductions[0].account, expected_account)
			self.assertEqual(payment_entry.deductions[0].amount, expected_amount)
			self.assertEqual(payment_entry.difference_amount, 0)

	def test_applies_withholding_tax_in_proportion_to_payment(self):
		invoice = self.make_invoice(
			"Sales Invoice",
			"Customer",
			"Vance Refrigeration",
			"WAREHOUSE-RENT",
			12000,
		)
		payment_entry = self.make_invoice_payment_entry(invoice, allocated_amount=6000)

		apply_thai_withholding_tax(payment_entry, invoice)

		self.assertEqual(payment_entry.paid_amount, 5700)
		self.assertEqual(payment_entry.received_amount, 5700)
		self.assertEqual(payment_entry.deductions[0].amount, 300)
		self.assertEqual(payment_entry.difference_amount, 0)

	def test_requires_withholding_tax_account(self):
		company = "Dunder Mifflin"
		frappe.db.set_value("Company", company, "sales_withholding_tax_account", None)
		frappe.clear_document_cache("Company", company)
		invoice = self.make_invoice(
			"Sales Invoice",
			"Customer",
			"Vance Refrigeration",
			"WAREHOUSE-RENT",
			12000,
		)
		payment_entry = self.make_invoice_payment_entry(invoice)

		try:
			with self.assertRaisesRegex(frappe.ValidationError, "Sales Withholding Tax Account"):
				apply_thai_withholding_tax(payment_entry, invoice)
		finally:
			frappe.clear_document_cache("Company", company)

	@staticmethod
	def make_invoice(doctype, party_type, party, item_code, amount):
		return frappe._dict(
			doctype=doctype,
			name="TEST-WHT-INVOICE",
			company="Dunder Mifflin",
			company_currency="THB",
			base_grand_total=amount,
			grand_total=amount,
			items=[frappe._dict(item_code=item_code, base_net_amount=amount)],
			**{frappe.scrub(party_type): party},
		)

	@staticmethod
	def make_invoice_payment_entry(invoice, allocated_amount=None):
		allocated_amount = allocated_amount or invoice.grand_total
		payment_type = "Receive" if invoice.doctype == "Sales Invoice" else "Pay"
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.update(
			{
				"company": invoice.company,
				"cost_center": frappe.get_cached_value("Company", invoice.company, "cost_center"),
				"payment_type": payment_type,
				"paid_from_account_currency": invoice.company_currency,
				"paid_to_account_currency": invoice.company_currency,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"paid_amount": allocated_amount,
				"received_amount": allocated_amount,
			}
		)
		payment_entry.append(
			"references",
			{
				"reference_doctype": invoice.doctype,
				"reference_name": invoice.name,
				"allocated_amount": allocated_amount,
				"exchange_rate": 1,
			},
		)
		return payment_entry
