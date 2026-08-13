from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry as erpnext_get_payment_entry,
)
from frappe.utils import add_days, nowdate

from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	apply_thai_withholding_tax,
	fetch_wht_detail,
	get_thai_withholding_tax_category,
)


class TestWithholdingTax(ERPNextThaiTestSuite):
	def assert_withholding_tax_deduction(
		self,
		deduction,
		reference_document,
		expected_amount,
		expected_account,
		expected_income_type,
		expected_rate,
		expected_base_amount,
	):
		reference_item = reference_document.get("items")[0]
		self.assertEqual(
			{
				"account": deduction.account,
				"amount": deduction.amount,
				"custom_is_withholding_tax_entry": deduction.custom_is_withholding_tax_entry,
				"custom_income_type": deduction.custom_income_type,
				"custom_tax_rate": deduction.custom_tax_rate,
				"custom_base_amount": deduction.custom_base_amount,
				"custom_reference_document_type": deduction.custom_reference_document_type,
				"custom_reference_document": deduction.custom_reference_document,
				"custom_reference_item_type": deduction.custom_reference_item_type,
				"custom_reference_item": deduction.custom_reference_item,
				"custom_item_code": deduction.custom_item_code,
			},
			{
				"account": expected_account,
				"amount": expected_amount,
				"custom_is_withholding_tax_entry": 1,
				"custom_income_type": expected_income_type,
				"custom_tax_rate": expected_rate,
				"custom_base_amount": expected_base_amount,
				"custom_reference_document_type": reference_document.doctype,
				"custom_reference_document": reference_document.name,
				"custom_reference_item_type": reference_item.doctype,
				"custom_reference_item": reference_item.name,
				"custom_item_code": reference_item.item_code,
			},
		)

	def test_party_withholding_tax_category_takes_precedence_over_company(self):
		with patch.object(frappe, "get_cached_value", return_value="Party Category") as get_cached_value:
			category = get_thai_withholding_tax_category("Customer", "Vance Refrigeration", "Dunder Mifflin")

		self.assertEqual(category, "Party Category")
		get_cached_value.assert_called_once_with(
			"Customer", "Vance Refrigeration", "custom_thai_withholding_tax_category"
		)

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

	def test_applies_thai_withholding_tax_to_invoice_and_order_payment_entries(self):
		for reference_document, expected_amount, expected_account, expected_income_type, expected_rate in (
			(
				self.make_reference_document(
					"Sales Invoice", "Customer", "Vance Refrigeration", "WAREHOUSE-RENT", 12000
				),
				600,
				"Sales Withholding Tax Receivable - DM",
				"5 ค่าเช่า",
				5,
			),
			(
				self.make_reference_document(
					"Sales Order", "Customer", "Vance Refrigeration", "WAREHOUSE-RENT", 12000
				),
				600,
				"Sales Withholding Tax Receivable - DM",
				"5 ค่าเช่า",
				5,
			),
			(
				self.make_reference_document(
					"Purchase Invoice",
					"Supplier",
					"Aaron Grandy",
					"LEGAL-CONSULTING-SERVICE",
					5000,
				),
				-150,
				"Purchase Withholding Tax PND 3 Payable - DM",
				"6 เงินได้จากวิชาชีพอิสระ",
				3,
			),
			(
				self.make_reference_document(
					"Purchase Order",
					"Supplier",
					"Aaron Grandy",
					"LEGAL-CONSULTING-SERVICE",
					5000,
				),
				-150,
				"Purchase Withholding Tax PND 3 Payable - DM",
				"6 เงินได้จากวิชาชีพอิสระ",
				3,
			),
		):
			payment_entry = self.make_reference_payment_entry(reference_document)

			apply_thai_withholding_tax(payment_entry, reference_document)

			self.assert_withholding_tax_deduction(
				payment_entry.deductions[0],
				reference_document,
				expected_amount,
				expected_account,
				expected_income_type,
				expected_rate,
				reference_document.grand_total,
			)
			self.assertEqual(payment_entry.difference_amount, 0)

	def test_order_payment_entry_override_applies_withholding_tax(self):
		for order, expected_amount, expected_account, expected_income_type, expected_rate in (
			(
				self.make_order("Sales Order", "Customer", "Vance Refrigeration", "WAREHOUSE-RENT", 12000),
				600,
				"Sales Withholding Tax Receivable - DM",
				"5 ค่าเช่า",
				5,
			),
			(
				self.make_order(
					"Purchase Order",
					"Supplier",
					"Aaron Grandy",
					"LEGAL-CONSULTING-SERVICE",
					5000,
				),
				-150,
				"Purchase Withholding Tax PND 3 Payable - DM",
				"6 เงินได้จากวิชาชีพอิสระ",
				3,
			),
		):
			bank_account = frappe.get_cached_value("Company", order.company, "default_cash_account")
			withholding_payment_entry = get_payment_entry(
				order.doctype, order.name, bank_account=bank_account
			)
			standard_payment_entry = erpnext_get_payment_entry(
				order.doctype, order.name, bank_account=bank_account
			)

			self.assertEqual(len(withholding_payment_entry.deductions), 1)
			self.assert_withholding_tax_deduction(
				withholding_payment_entry.deductions[0],
				order,
				expected_amount,
				expected_account,
				expected_income_type,
				expected_rate,
				order.base_grand_total,
			)
			self.assertEqual(withholding_payment_entry.difference_amount, 0)
			self.assertEqual(
				withholding_payment_entry.paid_amount,
				standard_payment_entry.paid_amount - abs(expected_amount),
			)

	@staticmethod
	def make_order(doctype, party_type, party, item_code, amount):
		order = frappe.new_doc(doctype)
		order.update(
			{
				"company": "Dunder Mifflin",
				frappe.scrub(party_type): party,
				"transaction_date": nowdate(),
				"currency": "THB",
				"conversion_rate": 1,
			}
		)
		if doctype == "Sales Order":
			order.delivery_date = add_days(nowdate(), 1)
		else:
			order.schedule_date = add_days(nowdate(), 1)
		order.append("items", {"item_code": item_code, "qty": 1, "rate": amount})
		order.insert()
		order.submit()
		return order

	def test_applies_withholding_tax_in_proportion_to_payment(self):
		invoice = self.make_reference_document(
			"Sales Invoice",
			"Customer",
			"Vance Refrigeration",
			"WAREHOUSE-RENT",
			12000,
		)
		payment_entry = self.make_reference_payment_entry(invoice, allocated_amount=6000)

		apply_thai_withholding_tax(payment_entry, invoice)

		self.assertEqual(payment_entry.paid_amount, 5700)
		self.assertEqual(payment_entry.received_amount, 5700)
		self.assertEqual(payment_entry.deductions[0].amount, 300)
		self.assertEqual(payment_entry.difference_amount, 0)

	def test_requires_withholding_tax_account(self):
		company = "Dunder Mifflin"
		frappe.db.set_value("Company", company, "sales_withholding_tax_account", None)
		frappe.clear_document_cache("Company", company)
		invoice = self.make_reference_document(
			"Sales Invoice",
			"Customer",
			"Vance Refrigeration",
			"WAREHOUSE-RENT",
			12000,
		)
		payment_entry = self.make_reference_payment_entry(invoice)

		try:
			with self.assertRaisesRegex(frappe.ValidationError, "Sales Withholding Tax Account"):
				apply_thai_withholding_tax(payment_entry, invoice)
		finally:
			frappe.clear_document_cache("Company", company)

	@staticmethod
	def make_reference_document(doctype, party_type, party, item_code, amount):
		return frappe._dict(
			doctype=doctype,
			name="TEST-WHT-INVOICE",
			company="Dunder Mifflin",
			company_currency="THB",
			base_grand_total=amount,
			grand_total=amount,
			items=[
				frappe._dict(
					doctype=f"{doctype} Item",
					name="TEST-WHT-INVOICE-ITEM",
					item_code=item_code,
					base_net_amount=amount,
				)
			],
			**{frappe.scrub(party_type): party},
		)

	@staticmethod
	def make_reference_payment_entry(reference_document, allocated_amount=None):
		allocated_amount = allocated_amount or reference_document.grand_total
		payment_type = "Receive" if reference_document.doctype in ("Sales Invoice", "Sales Order") else "Pay"
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.update(
			{
				"company": reference_document.company,
				"cost_center": frappe.get_cached_value("Company", reference_document.company, "cost_center"),
				"payment_type": payment_type,
				"paid_from_account_currency": reference_document.company_currency,
				"paid_to_account_currency": reference_document.company_currency,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"paid_amount": allocated_amount,
				"received_amount": allocated_amount,
			}
		)
		payment_entry.append(
			"references",
			{
				"reference_doctype": reference_document.doctype,
				"reference_name": reference_document.name,
				"allocated_amount": allocated_amount,
				"exchange_rate": 1,
			},
		)
		return payment_entry
