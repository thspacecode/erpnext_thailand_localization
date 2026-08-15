from pathlib import Path
from typing import TYPE_CHECKING

import frappe
from frappe.utils import add_days, getdate, now_datetime
from frappe.utils.file_manager import save_file

from erpnext_thailand_localization.data.abc import BaseImporter, Report
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)
from erpnext_thailand_localization.types import Json

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from frappe.model.document import Document
	from frappe.utils import DateTimeLikeObject

	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)

	type Invoice = SalesInvoice | PurchaseInvoice


class BaseTestRecord:
	"""Reusable base documents for tests and test-data bootstrap."""

	@staticmethod
	def insert_doc(doc_dict: "Json[Document]") -> "Document":
		doc = frappe.new_doc(doctype=doc_dict.get("doctype"))
		doc.update(doc_dict)
		doc.save()
		return doc

	@staticmethod
	def sales_invoice(
		customer: str,
		customer_po_no: str,
		items: list[tuple[str, int]],
		posting_date: "DateTimeLikeObject | None" = None,
	) -> "Json[SalesInvoice]":
		posting_date = getdate(posting_date)
		return {
			"doctype": "Sales Invoice",
			"company": "Dunder Mifflin",
			"customer": customer,
			"po_no": customer_po_no,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, 30),
			"currency": "THB",
			"conversion_rate": 1,
			"remarks": f"Dunder Mifflin mock invoice: {customer_po_no}",
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"rate": rate,
					"price_list_rate": rate,
				}
				for item_code, rate in items
			],
		}

	@staticmethod
	def purchase_invoice(
		supplier: str,
		supplier_invoice_no: str,
		items: list[tuple[str, int]],
		posting_date: "DateTimeLikeObject | None" = None,
	) -> "Json[PurchaseInvoice]":
		posting_date = getdate(posting_date)
		return {
			"doctype": "Purchase Invoice",
			"company": "Dunder Mifflin",
			"supplier": supplier,
			"bill_no": supplier_invoice_no,
			"bill_date": posting_date,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, 30),
			"currency": "THB",
			"conversion_rate": 1,
			"remarks": f"Dunder Mifflin mock purchase: {supplier_invoice_no}",
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"rate": rate,
					"price_list_rate": rate,
				}
				for item_code, rate in items
			],
		}

	@staticmethod
	def payment_entry(
		invoice: "Invoice",
		bank_account: str,
		posting_date: "DateTimeLikeObject | None" = None,
	) -> "Json[PaymentEntry]":
		posting_date = getdate(posting_date)
		payment_entry = get_payment_entry(
			invoice.doctype,
			invoice.name,
			bank_account=bank_account,
			reference_date=posting_date,
		)
		payment_entry.reference_no = f"MOCK-{invoice.name}"
		payment_entry.reference_date = posting_date
		return payment_entry.as_dict()

	@staticmethod
	def purchase_withholding_tax_entry(
		payment_entry: "PaymentEntry",
	) -> "Json[PurchaseWithholdingTaxEntry]":
		entry = make_purchase_withholding_tax_entry(payment_entry.name)
		entry.naming_series = "PWHT-.YYYY.-.#####"
		return entry.as_dict()

	@staticmethod
	def sales_withholding_tax_entry(
		invoice: "SalesInvoice",
		payment_entry: "PaymentEntry",
		certificate_number: str,
	) -> "Json[SalesWithholdingTaxEntry]":
		delivery_item = next(item for item in invoice.items if item.item_code == "DELIVERY-SERVICE")
		entry = make_sales_withholding_tax_entry(payment_entry.name)
		entry.naming_series = "SWHT-.YYYY.-.#####"
		entry.certificate_number = certificate_number
		entry.customer_address = entry.customer_address or invoice.customer_address
		entry.append(
			"items",
			{
				"income_type": "8 อื่นๆ",
				"base_amount": 12000,
				"tax_rate": 3,
				"reference_doc_doctype": invoice.doctype,
				"reference_doc": invoice.name,
				"reference_doc_item_doctype": delivery_item.doctype,
				"reference_doc_item": delivery_item.name,
			},
		)
		return entry.as_dict()


class BootStrapTestMasterData(BaseImporter):
	"""Set up reusable ERPNext prerequisites for development and tests."""

	data_csv_path = Path(__file__).parent / "data_csv"

	def define_share_val(self) -> None:
		self.now = now_datetime()

		# This mock company sells paper products.
		# The boss is the world's best boss, Michael Scott.
		# When creating mock data, ensure it is relevant to the company's business.
		self.company = "Dunder Mifflin"
		self.company_abbr = "DM"

		self.m = BaseTestRecord

	def make(self) -> Report:
		self.define_share_val()

		self.hotfix_standard_price()

		self.complete_setup_wizard()
		self.complete_module_onboarding()

		self.make_account()

		self.update_company()

		self.make_customer()
		self.make_supplier()
		self.make_item()
		self.make_party_addresses()

		frappe.db.commit()  # nosemgrep

		return self.report

	# ---
	# Maker Method
	# ---

	def hotfix_standard_price(self) -> None:
		"""Pre-seed ERPNext defaults required before its setup wizard runs."""
		self.csv_loader("Price List")

	def complete_setup_wizard(self) -> None:
		if frappe.is_setup_complete():
			return

		from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

		current_year = self.now.year
		setup_complete(
			{
				"currency": "THB",
				"country": "Thailand",
				"timezone": "Asia/Bangkok",
				"language": "English",
				"company_name": self.company,
				"company_abbr": self.company_abbr,
				"chart_of_accounts": "Standard",
				"fy_start_date": f"{current_year}-01-01",
				"fy_end_date": f"{current_year}-12-31",
				"setup_demo": 0,
			}
		)

	def complete_module_onboarding(self) -> None:
		for name in frappe.get_all(
			"Module Onboarding",
			filters={"is_complete": 0},
			pluck="name",
		):
			doc = frappe.get_doc("Module Onboarding", name)
			for step in doc.get_steps():
				step.db_set("is_complete", 1)
			doc.db_set("is_complete", 1)

	def make_account(self) -> None:
		self.csv_loader(
			"Account",
			csv_replacements={
				"company": self.company,
				"company_abbr": self.company_abbr,
				"asset_root": self.get_root_account("Asset"),
				"liability_root": self.get_root_account("Liability"),
			},
		)

	def update_company(self) -> None:
		company = frappe.get_doc("Company", self.company)
		company.update(
			{
				"tax_id": "0105555000001",
				"custom_thai_withholding_tax_category": "Juristic Person - Domestic",
				"sales_withholding_tax_account": (f"Sales Withholding Tax Receivable - {self.company_abbr}"),
				"purchase_withholding_tax_pnd3_account": (
					f"Purchase Withholding Tax PND 3 Payable - {self.company_abbr}"
				),
				"purchase_withholding_tax_pnd53_account": (
					f"Purchase Withholding Tax PND 53 Payable - {self.company_abbr}"
				),
			}
		)
		company.save()

	def make_customer(self) -> None:
		self.csv_loader("Customer")

	def make_supplier(self) -> None:
		self.csv_loader("Supplier")

	def make_item(self) -> None:
		self.csv_loader("Item")

	def make_party_addresses(self) -> None:
		self.csv_loader("Address")

	# ---
	# Helper Method
	# ---

	def get_root_account(self, root_type: str) -> str:
		root_accounts = [
			account
			for account in frappe.get_all(
				"Account",
				filters={"company": self.company, "root_type": root_type, "is_group": 1},
				fields=["name", "account_name", "parent_account"],
				order_by="lft asc",
			)
			if not account.parent_account
		]
		if not root_accounts:
			frappe.throw(f"No {root_type} root account exists for Company {self.company}.")

		matching_root = next(
			(account for account in root_accounts if account.account_name == root_type),
			root_accounts[0],
		)
		return matching_root.name

	def get_leaf_account(self, root_type: str, account_type: str | None = None) -> str:
		filters = {
			"company": self.company,
			"root_type": root_type,
			"is_group": 0,
			"disabled": 0,
		}
		if account_type:
			filters["account_type"] = account_type

		account = frappe.db.get_value("Account", filters, "name", order_by="lft asc")
		if not account and account_type:
			filters.pop("account_type")
			account = frappe.db.get_value("Account", filters, "name", order_by="lft asc")
		if not account:
			frappe.throw(f"No active {root_type} account exists for Company {self.company}.")
		return account

	def get_company_account(self, default_field: str, root_type: str, account_type: str) -> str:
		account = frappe.get_cached_value("Company", self.company, default_field)
		if account and not frappe.get_cached_value("Account", account, "is_group"):
			return account
		return self.get_leaf_account(root_type, account_type)


class BootStrapDevData(BootStrapTestMasterData):
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
		records = [
			self.m.sales_invoice(
				customer="Dunmore High School",
				customer_po_no="DM-MOCK-DUNMORE-PAPER-DELIVERY",
				items=[
					("DM-PREMIUM-COPY-PAPER", 10000),
					("DELIVERY-SERVICE", 12000),
				],
				posting_date=self.now,
			),
			self.m.sales_invoice(
				customer="Vance Refrigeration",
				customer_po_no="DM-MOCK-VANCE-WAREHOUSE-RENT",
				items=[("WAREHOUSE-RENT", 12000)],
				posting_date=self.now,
			),
		]
		documents = []
		for r in records:
			doc = frappe.new_doc("Sales Invoice")
			doc.update(r)
			doc.set_missing_values()
			doc.insert()
			doc.submit()
			documents.append(doc)
		return documents

	def make_purchase_invoice(self) -> list["PurchaseInvoice"]:
		records = [
			self.m.purchase_invoice(
				supplier="Aaron Grandy",
				supplier_invoice_no="AG-LEGAL-CONSULTING-UNPAID-001",
				items=[("LEGAL-CONSULTING-SERVICE", 5000)],
				posting_date=self.now,
			),
			self.m.purchase_invoice(
				supplier="Aaron Grandy",
				supplier_invoice_no="AG-LEGAL-CONSULTING-PAID-001",
				items=[("LEGAL-CONSULTING-SERVICE", 5000)],
				posting_date=self.now,
			),
		]
		documents = []
		for r in records:
			doc = frappe.new_doc("Purchase Invoice")
			doc.update(r)
			doc.set_missing_values()
			doc.insert()
			doc.submit()
			documents.append(doc)
		return documents

	def make_payment_entry(self, invoice: "Invoice") -> list["PaymentEntry"]:
		records = [
			self.m.payment_entry(
				invoice=invoice,
				bank_account=self.get_company_account("default_cash_account", "Asset", "Cash"),
				posting_date=self.now,
			),
		]
		documents = []
		for r in records:
			doc = frappe.new_doc("Payment Entry")
			doc.update(r)
			doc.insert()
			doc.submit()
			documents.append(doc)
		return documents

	def make_purchase_withholding_tax_entry(
		self, payment_entry: "PaymentEntry"
	) -> list["PurchaseWithholdingTaxEntry"]:
		records = [self.m.purchase_withholding_tax_entry(payment_entry)]
		documents = []
		for r in records:
			doc = frappe.new_doc("Purchase Withholding Tax Entry")
			doc.update(r)
			doc.insert()
			doc.submit()
			documents.append(doc)
		return documents

	def make_sales_withholding_tax_entry(
		self, invoice: "SalesInvoice", payment_entry: "PaymentEntry"
	) -> list["SalesWithholdingTaxEntry"]:
		certificate_number = "DUNMORE-WHT-0001"
		records = [
			self.m.sales_withholding_tax_entry(
				invoice=invoice,
				payment_entry=payment_entry,
				certificate_number=certificate_number,
			),
		]
		documents = []
		for r in records:
			doc = frappe.new_doc("Sales Withholding Tax Entry")
			doc.update(r)
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
			documents.append(doc)
		return documents
