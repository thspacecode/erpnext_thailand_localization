from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry as erpnext_get_payment_entry,
)

from erpnext_thailand_localization.tests.factories import (
	PaymentEntryFactory,
	PurchaseOrderFactory,
	SalesOrderFactory,
)
from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	apply_thai_withholding_tax,
	fetch_wht_detail,
	get_thai_withholding_tax_category,
	get_wht_rate,
)

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.payment_entry_deduction.payment_entry_deduction import (
		PaymentEntryDeduction,
	)
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
	from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

	type ReferenceDocument = SalesInvoice | SalesOrder | PurchaseInvoice | PurchaseOrder


class TestWithholdingTax(ERPNextThaiTestSuite):
	def assert_withholding_tax_deduction(
		self,
		deduction: "PaymentEntryDeduction",
		reference_document: "ReferenceDocument",
		expected_amount: float,
		expected_account: str,
		expected_income_type: str,
		expected_rate: float,
		expected_base_amount: float,
	) -> None:
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

	def test_sales_withholding_tax_uses_company_category(self) -> None:
		with patch.object(frappe, "get_cached_value", return_value="Company Category") as get_cached_value:
			category = get_thai_withholding_tax_category("Customer", "Vance Refrigeration", "Dunder Mifflin")

		self.assertEqual(category, "Company Category")
		get_cached_value.assert_called_once_with(
			"Company", "Dunder Mifflin", "custom_thai_withholding_tax_category"
		)

	def test_purchase_withholding_tax_uses_supplier_category(self) -> None:
		with patch.object(frappe, "get_cached_value", return_value="Supplier Category") as get_cached_value:
			category = get_thai_withholding_tax_category("Supplier", "Aaron Grandy", "Dunder Mifflin")

		self.assertEqual(category, "Supplier Category")
		get_cached_value.assert_called_once_with(
			"Supplier", "Aaron Grandy", "custom_thai_withholding_tax_category"
		)

	def test_fetch_wht_detail(self) -> None:
		self.assertEqual(
			fetch_wht_detail(
				"WAREHOUSE-RENT",
				party_type="Customer",
				party="Vance Refrigeration",
				company="Dunder Mifflin",
			),
			{"income_type": "5 ค่าเช่า", "tax_rate": 5.0, "source": "Item"},
		)

	def test_requires_category_for_reference_items_with_income_type(self) -> None:
		for reference_document, category_doctype, category_docname in (
			(
				self.make_reference_document(
					"Sales Invoice", "Customer", "Vance Refrigeration", "WAREHOUSE-RENT", 12000
				),
				"Company",
				"Dunder Mifflin",
			),
			(
				self.make_reference_document(
					"Purchase Invoice",
					"Supplier",
					"Aaron Grandy",
					"LEGAL-CONSULTING-SERVICE",
					5000,
				),
				"Supplier",
				"Aaron Grandy",
			),
		):
			with (
				self.subTest(reference_document.doctype),
				self.change_settings(
					category_doctype,
					{"custom_thai_withholding_tax_category": None},
					docname=category_docname,
				),
			):
				payment_entry = self.make_reference_payment_entry(reference_document)
				with self.assertRaisesRegex(
					frappe.ValidationError,
					f"Please set Thai Withholding Tax Category for {category_doctype}",
				):
					apply_thai_withholding_tax(payment_entry, reference_document)

	def test_zero_rate_is_resolved_without_falling_back(self) -> None:
		for source, income_type, configured_rate, category_rates, category in (
			(
				"category rate",
				"5 ค่าเช่า",
				"5",
				[
					frappe._dict(
						thai_withholding_tax_category="Individual - Domestic",
						rate="0",
					)
				],
				"Individual - Domestic",
			),
			("configured default rate", "5 ค่าเช่า", "0", None, None),
			("income type default rate", "1 เงินเดือนค่าจ้าง เบี้ยเลี้ยง", None, None, None),
		):
			with self.subTest(source):
				self.assertEqual(
					get_wht_rate(income_type, configured_rate, category_rates, category),
					0,
				)

	def test_zero_rate_does_not_create_deduction(self) -> None:
		item_code = "WAREHOUSE-RENT"
		invoice = self.make_reference_document(
			"Sales Invoice", "Customer", "Vance Refrigeration", item_code, 12000
		)
		payment_entry = self.make_reference_payment_entry(invoice)

		with self.change_settings(
			"Item",
			{"custom_thai_withholding_tax_rate": "0"},
			docname=item_code,
		):
			apply_thai_withholding_tax(payment_entry, invoice)

		self.assertFalse(payment_entry.deductions)
		self.assertEqual(payment_entry.paid_amount, invoice.grand_total)
		self.assertEqual(payment_entry.received_amount, invoice.grand_total)

	def test_applies_thai_withholding_tax_to_invoice_and_order_payment_entries(
		self,
	) -> None:
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
			with self.subTest(f"applies withholding tax to {reference_document.doctype}"):
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

	def test_order_payment_entry_override_applies_withholding_tax(self) -> None:
		for order, expected_amount, expected_account, expected_income_type, expected_rate in (
			(
				SalesOrderFactory.create(
					customer="Vance Refrigeration",
					items=[{"item_code": "WAREHOUSE-RENT", "qty": 1, "rate": 12000}],
					submit=True,
				),
				600,
				"Sales Withholding Tax Receivable - DM",
				"5 ค่าเช่า",
				5,
			),
			(
				PurchaseOrderFactory.create(
					supplier="Aaron Grandy",
					items=[{"item_code": "LEGAL-CONSULTING-SERVICE", "qty": 1, "rate": 5000}],
					submit=True,
				),
				-150,
				"Purchase Withholding Tax PND 3 Payable - DM",
				"6 เงินได้จากวิชาชีพอิสระ",
				3,
			),
		):
			with self.subTest(f"applies withholding tax to {order.doctype}"):
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

	def test_payment_entry_override_respects_company_withholding_tax_settings(self) -> None:
		for order, setting_field in (
			(
				SalesOrderFactory.create(
					customer="Vance Refrigeration",
					items=[{"item_code": "WAREHOUSE-RENT", "qty": 1, "rate": 12000}],
					submit=True,
				),
				"enable_sales_withholding_tax",
			),
			(
				PurchaseOrderFactory.create(
					supplier="Aaron Grandy",
					items=[{"item_code": "LEGAL-CONSULTING-SERVICE", "qty": 1, "rate": 5000}],
					submit=True,
				),
				"enable_purchase_withholding_tax",
			),
		):
			with self.subTest(f"does not apply disabled withholding tax to {order.doctype}"):
				company = order.company
				original_value = frappe.db.get_value("Company", company, setting_field)
				frappe.db.set_value("Company", company, setting_field, 0)
				frappe.clear_document_cache("Company", company)
				try:
					bank_account = frappe.get_cached_value("Company", company, "default_cash_account")
					payment_entry = get_payment_entry(order.doctype, order.name, bank_account=bank_account)
				finally:
					frappe.db.set_value("Company", company, setting_field, original_value)
					frappe.clear_document_cache("Company", company)

				self.assertFalse(payment_entry.deductions)
				self.assertEqual(payment_entry.paid_amount, order.grand_total)

	def test_applies_withholding_tax_in_proportion_to_payment(self) -> None:
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

	def test_requires_withholding_tax_account(self) -> None:
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
	def make_reference_document(
		doctype: str, party_type: str, party: str, item_code: str, amount: float
	) -> "ReferenceDocument":
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
	def make_reference_payment_entry(
		reference_document: "ReferenceDocument",
		allocated_amount: float | None = None,
	) -> "PaymentEntry":
		if allocated_amount is None:
			allocated_amount = reference_document.grand_total
		payment_type = "Receive" if reference_document.doctype in ("Sales Invoice", "Sales Order") else "Pay"
		return PaymentEntryFactory.build(
			company=reference_document.company,
			cost_center=frappe.get_cached_value("Company", reference_document.company, "cost_center"),
			payment_type=payment_type,
			paid_from_account_currency=reference_document.company_currency,
			paid_to_account_currency=reference_document.company_currency,
			paid_amount=allocated_amount,
			received_amount=allocated_amount,
			references=[
				{
					"reference_doctype": reference_document.doctype,
					"reference_name": reference_document.name,
					"allocated_amount": allocated_amount,
					"exchange_rate": 1,
				}
			],
		)
