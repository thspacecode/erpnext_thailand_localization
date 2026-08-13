from abc import ABC, abstractmethod

import frappe
from frappe.utils import add_days, getdate

from erpnext_thailand_localization.data.test_data.bootstrap_test_data import BaseTestRecord
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)


class PaymentEntryTest:
	class TestCase(ERPNextThaiTestSuite, ABC):
		company = "Dunder Mifflin"
		company_currency = "THB"

		@abstractmethod
		def make_invoice(self, party, reference_number, item_code, amount):
			pass

		def assert_withholding_tax_entry(
			self,
			entry,
			payment_entry,
			invoice,
			party_field,
			party,
			address_field,
			address,
			income_type,
			base_amount,
			tax_rate,
		):
			self.assertEqual(entry.company, self.company)
			self.assertEqual(entry.company_currency, self.company_currency)
			self.assertEqual(entry.payment_date, getdate(payment_entry.posting_date))
			self.assertEqual(entry.get(party_field), party)
			self.assertEqual(entry.get(address_field), address)
			self.assertEqual(len(entry.items), 1)
			self.assertEqual(entry.items[0].income_type, income_type)
			self.assertEqual(entry.items[0].base_amount, base_amount)
			self.assertEqual(entry.items[0].tax_rate, tax_rate)
			self.assertEqual(entry.items[0].reference_doc_doctype, invoice.doctype)
			self.assertEqual(entry.items[0].reference_doc, invoice.name)
			self.assertEqual(entry.items[0].reference_doc_item_doctype, invoice.items[0].doctype)
			self.assertEqual(entry.items[0].reference_doc_item, invoice.items[0].name)

		@staticmethod
		def insert_invoice(values):
			invoice = frappe.get_doc(values)
			invoice.set_missing_values()
			invoice.insert()
			invoice.submit()
			return invoice

		def make_payment_entry(self, invoice, allocated_amount=None, submit=True):
			payment_entry = frappe.get_doc(
				BaseTestRecord.payment_entry(
					invoice,
					bank_account=frappe.get_cached_value("Company", self.company, "default_cash_account"),
				)
			)
			if allocated_amount is not None:
				payment_entry.references[0].allocated_amount = allocated_amount
				payment_entry.paid_amount = allocated_amount
				payment_entry.received_amount = allocated_amount
				payment_entry.set_amounts()
			payment_entry.insert()
			if submit:
				payment_entry.submit()
			return payment_entry


class TestSellingPaymentEntry(PaymentEntryTest.TestCase):
	customer = "Vance Refrigeration"
	customer_address = "Vance Refrigeration-Billing"
	item_code = "WAREHOUSE-RENT"
	income_type = "5 ค่าเช่า"

	def make_invoice(self, customer, reference_number, item_code, amount):
		return self.insert_invoice(
			BaseTestRecord.sales_invoice(
				customer=customer,
				customer_po_no=reference_number,
				items=[(item_code, amount)],
			)
		)

	def make_order(self, customer, item_code, amount):
		return self.insert_invoice(
			{
				"doctype": "Sales Order",
				"company": self.company,
				"customer": customer,
				"delivery_date": add_days(getdate(), 1),
				"currency": self.company_currency,
				"conversion_rate": 1,
				"items": [{"item_code": item_code, "qty": 1, "rate": amount}],
			}
		)

	def test_make_sales_withholding_tax_entry_for_partial_payment(self):
		invoice = self.make_invoice(
			self.customer,
			"TEST-SALES-WHT-MAPPER",
			self.item_code,
			12000,
		)
		payment_entry = self.make_payment_entry(invoice, allocated_amount=6000)

		entry = make_sales_withholding_tax_entry(payment_entry.name)

		self.assert_withholding_tax_entry(
			entry,
			payment_entry,
			invoice,
			party_field="customer",
			party=self.customer,
			address_field="customer_address",
			address=self.customer_address,
			income_type=self.income_type,
			base_amount=6000,
			tax_rate=5,
		)
		self.assertEqual(entry.total_base_amount, 6000)
		self.assertEqual(entry.total_tax_amount, 300)

	def test_make_sales_withholding_tax_entry_from_sales_order(self):
		order = self.make_order(self.customer, self.item_code, 12000)
		payment_entry = self.make_payment_entry(order)

		entry = make_sales_withholding_tax_entry(payment_entry.name)

		self.assert_withholding_tax_entry(
			entry,
			payment_entry,
			order,
			party_field="customer",
			party=self.customer,
			address_field="customer_address",
			address=self.customer_address,
			income_type=self.income_type,
			base_amount=12000,
			tax_rate=5,
		)
		self.assertEqual(entry.total_base_amount, 12000)
		self.assertEqual(entry.total_tax_amount, 600)

	def test_make_withholding_tax_entry_requires_submitted_payment_entry(self):
		invoice = self.make_invoice(
			self.customer,
			"TEST-DRAFT-PAYMENT-WHT-MAPPER",
			self.item_code,
			12000,
		)
		payment_entry = self.make_payment_entry(invoice, submit=False)

		with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
			make_sales_withholding_tax_entry(payment_entry.name)


class TestBuyingPaymentEntry(PaymentEntryTest.TestCase):
	supplier = "Aaron Grandy"
	supplier_address = "Aaron Grandy-Billing"
	item_code = "LEGAL-CONSULTING-SERVICE"
	income_type = "6 เงินได้จากวิชาชีพอิสระ"

	def make_invoice(self, supplier, reference_number, item_code, amount):
		return self.insert_invoice(
			BaseTestRecord.purchase_invoice(
				supplier=supplier,
				supplier_invoice_no=reference_number,
				items=[(item_code, amount)],
			)
		)

	def make_order(self, supplier, item_code, amount):
		return self.insert_invoice(
			{
				"doctype": "Purchase Order",
				"company": self.company,
				"supplier": supplier,
				"schedule_date": add_days(getdate(), 1),
				"currency": self.company_currency,
				"conversion_rate": 1,
				"items": [{"item_code": item_code, "qty": 1, "rate": amount}],
			}
		)

	def test_make_purchase_withholding_tax_entry(self):
		invoice = self.make_invoice(
			self.supplier,
			"TEST-PURCHASE-WHT-MAPPER",
			self.item_code,
			5000,
		)
		payment_entry = self.make_payment_entry(invoice)

		entry = make_purchase_withholding_tax_entry(payment_entry.name)

		self.assert_withholding_tax_entry(
			entry,
			payment_entry,
			invoice,
			party_field="supplier",
			party=self.supplier,
			address_field="supplier_address",
			address=self.supplier_address,
			income_type=self.income_type,
			base_amount=5000,
			tax_rate=3,
		)

	def test_make_purchase_withholding_tax_entry_from_purchase_order(self):
		order = self.make_order(self.supplier, self.item_code, 5000)
		payment_entry = self.make_payment_entry(order)

		entry = make_purchase_withholding_tax_entry(payment_entry.name)

		self.assert_withholding_tax_entry(
			entry,
			payment_entry,
			order,
			party_field="supplier",
			party=self.supplier,
			address_field="supplier_address",
			address=self.supplier_address,
			income_type=self.income_type,
			base_amount=5000,
			tax_rate=3,
		)
		self.assertEqual(entry.total_base_amount, 5000)
		self.assertEqual(entry.total_tax_amount, 150)

	def test_make_withholding_tax_entry_requires_submitted_payment_entry(self):
		invoice = self.make_invoice(
			self.supplier,
			"TEST-DRAFT-PAYMENT-WHT-MAPPER",
			self.item_code,
			5000,
		)
		payment_entry = self.make_payment_entry(invoice, submit=False)

		with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
			make_purchase_withholding_tax_entry(payment_entry.name)
