from typing import TYPE_CHECKING

from frappe.utils import add_days
from frappe.utils.file_manager import save_file

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.test_data.bootstrap_test_master_data import BootStrapTestMasterData
from erpnext_thailand_localization.tests.factories import PurchaseInvoiceFactory, SalesInvoiceFactory
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)

	type Invoice = SalesInvoice | PurchaseInvoice


class BootStrapDevData(BootStrapTestMasterData):
	"""Set up transaction for development. Avoid using these transaction in test case."""

	def make(self) -> Report:
		self.define_share_val()

		sales_invoices = self.make_sales_invoice()
		paper_invoice = next(
			invoice for invoice in sales_invoices if invoice.customer == "Dunmore High School"
		)
		payment_entries = self.make_payment_entry(paper_invoice)
		self.make_sales_withholding_tax_entry(paper_invoice, payment_entries[0])

		purchase_invoices = self.make_purchase_invoice()
		paid_purchase_invoice = next(
			invoice for invoice in purchase_invoices if invoice.bill_no == "AG-LEGAL-CONSULTING-PAID-001"
		)
		purchase_payment = self.make_payment_entry(paid_purchase_invoice)[0]
		self.make_purchase_withholding_tax_entry(purchase_payment)

		return self.report

	def make_sales_invoice(self) -> list["SalesInvoice"]:
		return [
			SalesInvoiceFactory.create(
				customer="Dunmore High School",
				po_no="DM-MOCK-DUNMORE-PAPER-DELIVERY",
				posting_date=self.now,
				due_date=add_days(self.now, 30),
				remarks="Dunder Mifflin mock invoice: DM-MOCK-DUNMORE-PAPER-DELIVERY",
				items=[
					{
						"item_code": "DM-PREMIUM-COPY-PAPER",
						"qty": 1,
						"rate": 10000,
						"price_list_rate": 10000,
					},
					{
						"item_code": "DELIVERY-SERVICE",
						"qty": 1,
						"rate": 12000,
						"price_list_rate": 12000,
					},
				],
				submit=True,
			),
			SalesInvoiceFactory.create(
				customer="Vance Refrigeration",
				po_no="DM-MOCK-VANCE-WAREHOUSE-RENT",
				posting_date=self.now,
				due_date=add_days(self.now, 30),
				remarks="Dunder Mifflin mock invoice: DM-MOCK-VANCE-WAREHOUSE-RENT",
				items=[
					{
						"item_code": "WAREHOUSE-RENT",
						"qty": 1,
						"rate": 12000,
						"price_list_rate": 12000,
					}
				],
				submit=True,
			),
		]

	def make_purchase_invoice(self) -> list["PurchaseInvoice"]:
		invoices = []
		for bill_no in ("AG-LEGAL-CONSULTING-UNPAID-001", "AG-LEGAL-CONSULTING-PAID-001"):
			invoices.append(
				PurchaseInvoiceFactory.create(
					supplier="Aaron Grandy",
					bill_no=bill_no,
					bill_date=self.now,
					posting_date=self.now,
					due_date=add_days(self.now, 30),
					remarks=f"Dunder Mifflin mock purchase: {bill_no}",
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
			)
		return invoices

	def make_payment_entry(self, invoice: "Invoice") -> list["PaymentEntry"]:
		payment_entry = get_payment_entry(
			invoice.doctype,
			invoice.name,
			bank_account=self.get_company_account("default_cash_account", "Asset", "Cash"),
			reference_date=self.now,
		)
		payment_entry.reference_no = f"MOCK-{invoice.name}"
		payment_entry.reference_date = self.now
		payment_entry.insert()
		payment_entry.submit()
		return [payment_entry]

	def make_purchase_withholding_tax_entry(
		self, payment_entry: "PaymentEntry"
	) -> list["PurchaseWithholdingTaxEntry"]:
		doc = make_purchase_withholding_tax_entry(payment_entry.name)
		doc.naming_series = "PWHT-.YYYY.-.#####"
		doc.insert()
		doc.submit()
		return [doc]

	def make_sales_withholding_tax_entry(
		self,
		invoice: "SalesInvoice",
		payment_entry: "PaymentEntry",
	) -> list["SalesWithholdingTaxEntry"]:
		certificate_number = "DUNMORE-WHT-0001"
		doc = make_sales_withholding_tax_entry(payment_entry.name)
		doc.naming_series = "SWHT-.YYYY.-.#####"
		doc.certificate_number = certificate_number
		doc.customer_address = doc.customer_address or invoice.customer_address
		doc.insert()

		certificate_content = (
			"MOCK THAI WITHHOLDING TAX CERTIFICATE\n"
			f"Certificate Number: {certificate_number}\n"
			"Customer: Dunmore High School\n"
			f"Payment Entry: {payment_entry.name}\n"
			"Withholding Tax Base: THB 12,000.00\n"
			"Withholding Tax Rate: 3%\n"
			"Withholding Tax Amount: THB 360.00\n"
		).encode()
		certificate_file = save_file(
			f"{certificate_number}.txt",
			certificate_content,
			doc.doctype,
			doc.name,
			is_private=1,
		)
		doc.certificate_attachment = certificate_file.file_url
		doc.save()
		doc.submit()
		return [doc]
