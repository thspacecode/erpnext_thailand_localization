from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.utils import getdate

from erpnext_thailand_localization.tests.factories import (
	PurchaseInvoiceFactory,
	PurchaseOrderFactory,
	SalesInvoiceFactory,
	SalesOrderFactory,
)
from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.payment_entry import (
	get_withholding_tax_from_references,
)

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
	from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.model.withholding_tax_entry import (
		WithholdingTaxEntry,
	)

	type Invoice = SalesInvoice | PurchaseInvoice
	type ReferenceDocument = Invoice | SalesOrder | PurchaseOrder


def create_payment_entry_from_reference(
	reference_document: "ReferenceDocument",
	allocated_amount: float | None = None,
	*,
	submit: bool = True,
) -> "PaymentEntry":
	bank_account = frappe.get_cached_value(
		"Company", reference_document.company, "default_cash_account"
	)
	posting_date = getdate()
	payment_entry = get_payment_entry(
		reference_document.doctype,
		reference_document.name,
		bank_account=bank_account,
		reference_date=posting_date,
	)
	payment_entry.reference_no = f"MOCK-{reference_document.name}"
	payment_entry.reference_date = posting_date
	if allocated_amount is not None:
		payment_entry.references[0].allocated_amount = allocated_amount
		payment_entry.paid_amount = allocated_amount
		payment_entry.received_amount = allocated_amount
		payment_entry.set_amounts()
	payment_entry.insert()
	if submit:
		payment_entry.submit()
	return payment_entry


class PaymentEntryTest:
	class TestCase(ERPNextThaiTestSuite, ABC):
		company = "Dunder Mifflin"
		company_currency = "THB"

		@abstractmethod
		def make_invoice(self, party: str, reference_number: str, item_code: str, amount: float) -> "Invoice":
			pass

		def assert_withholding_tax_entry(
			self,
			entry: "WithholdingTaxEntry",
			payment_entry: "PaymentEntry",
			invoice: "ReferenceDocument",
			party_field: str,
			party: str,
			address_field: str,
			address: str,
			income_type: str,
			base_amount: float,
			tax_rate: float,
		) -> None:
			self.assertEqual(entry.company, self.company)
			self.assertEqual(entry.company_currency, self.company_currency)
			self.assertEqual(entry.payment_date, getdate(payment_entry.posting_date))
			self.assertEqual(entry.get(party_field), party)
			self.assertEqual(entry.get(address_field), address)
			self.assertEqual(len(entry.items), 1)
			self.assertEqual(entry.items[0].income_type, income_type)
			self.assertEqual(entry.items[0].base_amount, base_amount)
			self.assertEqual(entry.items[0].tax_rate, tax_rate)
			deduction = next(row for row in payment_entry.deductions if row.custom_is_withholding_tax_entry)
			self.assertEqual(entry.items[0].reference_doc_doctype, "Payment Entry")
			self.assertEqual(entry.items[0].reference_doc, payment_entry.name)
			self.assertEqual(entry.items[0].reference_doc_item_doctype, "Payment Entry Deduction")
			self.assertEqual(entry.items[0].reference_doc_item, deduction.name)
			self.assertEqual(deduction.custom_reference_document_type, invoice.doctype)
			self.assertEqual(deduction.custom_reference_document, invoice.name)
			self.assertEqual(deduction.custom_reference_item_type, invoice.items[0].doctype)
			self.assertEqual(deduction.custom_reference_item, invoice.items[0].name)

		def make_payment_entry(
			self,
			invoice: "ReferenceDocument",
			allocated_amount: float | None = None,
			submit: bool = True,
		) -> "PaymentEntry":
			return create_payment_entry_from_reference(
				invoice, allocated_amount=allocated_amount, submit=submit
			)


class TestSellingPaymentEntry(PaymentEntryTest.TestCase):
	customer = "Vance Refrigeration"
	customer_address = "Vance Refrigeration-Billing"
	item_code = "WAREHOUSE-RENT"
	income_type = "5 ค่าเช่า"

	def make_invoice(
		self, customer: str, reference_number: str, item_code: str, amount: float
	) -> "SalesInvoice":
		return SalesInvoiceFactory.create(
			customer=customer,
			po_no=reference_number,
			items=[{"item_code": item_code, "qty": 1, "rate": amount, "price_list_rate": amount}],
			submit=True,
		)

	def test_make_sales_withholding_tax_entry_for_partial_payment(self) -> None:
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
			base_amount=12000,
			tax_rate=5,
		)
		self.assertEqual(entry.total_base_amount, 12000)
		self.assertEqual(entry.total_tax_amount, 600)

	def test_make_sales_withholding_tax_entry_from_sales_order(self) -> None:
		order = SalesOrderFactory.create(
			customer=self.customer,
			items=[{"item_code": self.item_code, "qty": 1, "rate": 12000}],
			submit=True,
		)
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

	def test_make_withholding_tax_entry_requires_submitted_payment_entry(self) -> None:
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

	def make_invoice(
		self, supplier: str, reference_number: str, item_code: str, amount: float
	) -> "PurchaseInvoice":
		return PurchaseInvoiceFactory.create(
			supplier=supplier,
			bill_no=reference_number,
			items=[{"item_code": item_code, "qty": 1, "rate": amount, "price_list_rate": amount}],
			submit=True,
		)

	def test_make_purchase_withholding_tax_entry(self) -> None:
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

	def test_make_purchase_withholding_tax_entry_from_purchase_order(self) -> None:
		order = PurchaseOrderFactory.create(
			supplier=self.supplier,
			items=[{"item_code": self.item_code, "qty": 1, "rate": 5000}],
			submit=True,
		)
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

	def test_make_withholding_tax_entry_requires_submitted_payment_entry(self) -> None:
		invoice = self.make_invoice(
			self.supplier,
			"TEST-DRAFT-PAYMENT-WHT-MAPPER",
			self.item_code,
			5000,
		)
		payment_entry = self.make_payment_entry(invoice, submit=False)

		with self.assertRaisesRegex(frappe.ValidationError, "must be submitted"):
			make_purchase_withholding_tax_entry(payment_entry.name)


class TestGetWithholdingTaxFromReferences(PaymentEntryTest.TestCase):
	supplier = "Aaron Grandy"
	item_code = "LEGAL-CONSULTING-SERVICE"
	income_type = "6 เงินได้จากวิชาชีพอิสระ"

	def make_invoice(
		self, supplier: str, reference_number: str, item_code: str, amount: float
	) -> "PurchaseInvoice":
		return PurchaseInvoiceFactory.create(
			supplier=supplier,
			bill_no=reference_number,
			items=[{"item_code": item_code, "qty": 1, "rate": amount, "price_list_rate": amount}],
			submit=True,
		)

	def test_single_reference(self) -> None:
		invoice = self.make_invoice(
			self.supplier,
			"TEST-GET-WHT-FROM-REFERENCES",
			self.item_code,
			5000,
		)
		payment_entry = self.make_payment_entry(invoice, allocated_amount=2500, submit=False)

		deductions = get_withholding_tax_from_references(payment_entry.as_dict())

		self.assertEqual(len(deductions), 1)
		self.assertEqual(deductions[0]["amount"], -75)
		self.assertEqual(deductions[0]["custom_base_amount"], 2500)
		self.assertEqual(deductions[0]["custom_income_type"], self.income_type)
		self.assertEqual(deductions[0]["custom_tax_rate"], 3)
		self.assertEqual(deductions[0]["custom_reference_document_type"], invoice.doctype)
		self.assertEqual(deductions[0]["custom_reference_document"], invoice.name)
		self.assertEqual(deductions[0]["custom_reference_item_type"], invoice.items[0].doctype)
		self.assertEqual(deductions[0]["custom_reference_item"], invoice.items[0].name)
		self.assertEqual(deductions[0]["custom_item_code"], self.item_code)

	def test_multiple_references_exclude_items_without_withholding_tax(self) -> None:
		invoices = [
			self.make_invoice(
				self.supplier,
				"TEST-GET-WHT-MULTIPLE-LEGAL",
				self.item_code,
				5000,
			),
			self.make_invoice(
				self.supplier,
				"TEST-GET-WHT-MULTIPLE-AUDIT",
				"AUDIT-FEE",
				4000,
			),
			self.make_invoice(
				self.supplier,
				"TEST-GET-WHT-MULTIPLE-PAPER",
				"DM-PREMIUM-COPY-PAPER",
				2000,
			),
		]
		allocated_amounts = [2500, 1000, 500]
		payment_entry = self.make_payment_entry(
			invoices[0], allocated_amount=allocated_amounts[0], submit=False
		)
		for invoice, allocated_amount in zip(invoices[1:], allocated_amounts[1:], strict=True):
			payment_entry.append(
				"references",
				{
					"reference_doctype": invoice.doctype,
					"reference_name": invoice.name,
					"total_amount": invoice.grand_total,
					"outstanding_amount": invoice.outstanding_amount,
					"allocated_amount": allocated_amount,
					"exchange_rate": 1,
				},
			)

		deductions = get_withholding_tax_from_references(payment_entry.as_dict())

		self.assertEqual(len(deductions), 2)
		self.assertEqual(
			[
				(
					deduction["custom_reference_document"],
					deduction["custom_base_amount"],
					deduction["amount"],
				)
				for deduction in deductions
			],
			[
				(invoices[0].name, 2500, -75),
				(invoices[1].name, 1000, -30),
			],
		)


class PaymentEntryDeductionMappingTestCase(ERPNextThaiTestSuite):
	company = "Dunder Mifflin"

	def make_payment_entry(self, invoice: "Invoice") -> "PaymentEntry":
		return create_payment_entry_from_reference(invoice)

	def assert_payment_entry_deduction_mapping(
		self, entry: "WithholdingTaxEntry", payment_entry: "PaymentEntry"
	) -> None:
		deduction = next(row for row in payment_entry.deductions if row.custom_is_withholding_tax_entry)
		self.assertEqual(len(entry.items), 1)
		self.assertEqual(entry.items[0].income_type, deduction.custom_income_type)
		self.assertEqual(entry.items[0].base_amount, deduction.custom_base_amount)
		self.assertEqual(entry.items[0].tax_rate, deduction.custom_tax_rate)
		self.assertEqual(entry.items[0].reference_doc_doctype, "Payment Entry")
		self.assertEqual(entry.items[0].reference_doc, payment_entry.name)
		self.assertEqual(entry.items[0].reference_doc_item_doctype, "Payment Entry Deduction")
		self.assertEqual(entry.items[0].reference_doc_item, deduction.name)


class TestSalesPaymentEntryDeductionMapping(PaymentEntryDeductionMappingTestCase):
	def make_payment_and_entry(self) -> tuple["PaymentEntry", "SalesWithholdingTaxEntry"]:
		invoice = SalesInvoiceFactory.create(
			customer="Vance Refrigeration",
			po_no="TEST-SALES-WHT-DEDUCTION-MAPPING",
			items=[
				{
					"item_code": "WAREHOUSE-RENT",
					"qty": 1,
					"rate": 12000,
					"price_list_rate": 12000,
				}
			],
			submit=True,
		)
		payment_entry = self.make_payment_entry(invoice)
		return payment_entry, make_sales_withholding_tax_entry(payment_entry.name)

	def test_maps_sales_payment_entry_deduction(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()
		self.assert_payment_entry_deduction_mapping(entry, payment_entry)

	def test_repeated_selection_does_not_duplicate_deduction(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()
		entry = make_sales_withholding_tax_entry(payment_entry.name, target_doc=entry)
		self.assertEqual(len(entry.items), 1)

	def test_rejects_mismatched_target_party_and_company(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()

		with self.subTest("rejects a target with a mismatched party"):
			entry.customer = "Lackawanna County"
			with self.assertRaisesRegex(frappe.ValidationError, "does not belong"):
				make_sales_withholding_tax_entry(payment_entry.name, target_doc=entry)

		with self.subTest("rejects a target with a mismatched company"):
			entry.customer = payment_entry.party
			entry.company = "Another Company"
			with self.assertRaisesRegex(frappe.ValidationError, "does not belong"):
				make_sales_withholding_tax_entry(payment_entry.name, target_doc=entry)

	def test_validation_locks_payment_entry_for_concurrent_protection(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()
		with patch("frappe.get_doc", wraps=frappe.get_doc) as get_doc:
			entry.validate_payment_entry_deductions()

		get_doc.assert_any_call("Payment Entry", payment_entry.name, for_update=True)


class TestPurchasePaymentEntryDeductionMapping(PaymentEntryDeductionMappingTestCase):
	def make_payment_and_entry(self) -> tuple["PaymentEntry", "PurchaseWithholdingTaxEntry"]:
		invoice = PurchaseInvoiceFactory.create(
			supplier="Aaron Grandy",
			bill_no="TEST-PURCHASE-WHT-DEDUCTION-MAPPING",
			items=[
				{
					"item_code": "LEGAL-CONSULTING-SERVICE",
					"qty": 1,
					"rate": 5000,
					"price_list_rate": 5000,
				}
			],
			submit=True,
		)
		payment_entry = self.make_payment_entry(invoice)
		return payment_entry, make_purchase_withholding_tax_entry(payment_entry.name)

	def test_maps_purchase_payment_entry_deduction(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()
		self.assert_payment_entry_deduction_mapping(entry, payment_entry)

	def test_duplicate_deduction_within_current_entry_is_rejected(self) -> None:
		_, entry = self.make_payment_and_entry()
		duplicate_values = entry.items[0].as_dict()
		for fieldname in ("name", "parent", "parenttype", "parentfield", "idx"):
			duplicate_values.pop(fieldname, None)
		entry.append("items", duplicate_values)
		with self.assertRaisesRegex(frappe.ValidationError, "referenced more than once"):
			entry.validate_payment_entry_deductions()

	def test_cross_document_duplicate_and_cancellation_reuse(self) -> None:
		payment_entry, entry = self.make_payment_and_entry()
		entry.supplier_address = entry.supplier_address or "Aaron Grandy-Billing"
		entry.insert()

		with self.subTest("rejects a deduction referenced by another active entry"):
			duplicate = make_purchase_withholding_tax_entry(payment_entry.name)
			duplicate.supplier_address = duplicate.supplier_address or "Aaron Grandy-Billing"
			with self.assertRaisesRegex(frappe.ValidationError, "already referenced"):
				duplicate.insert()

		with self.subTest("allows a deduction to be reused after cancellation"):
			entry.db_set("docstatus", 2)
			for item in entry.items:
				item.db_set("docstatus", 2)
			reusable = make_purchase_withholding_tax_entry(payment_entry.name)
			reusable.supplier_address = reusable.supplier_address or "Aaron Grandy-Billing"
			reusable.insert()
