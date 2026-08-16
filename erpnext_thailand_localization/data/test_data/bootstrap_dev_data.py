from typing import TYPE_CHECKING, TypedDict

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.utils import add_days, add_months, flt, get_first_day, getdate
from frappe.utils.file_manager import save_file

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.test_data.bootstrap_test_master_data import BootStrapTestMasterData
from erpnext_thailand_localization.tests.factories import (
	CompanyAddressFactory,
	PurchaseInvoiceFactory,
	SalesInvoiceFactory,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry import (
	get_payment_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing import (
	add_purchase_withholding_tax_entry_to_filing,
)

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from frappe.contacts.doctype.address.address import Address
	from frappe.utils import DateTimeLikeObject

	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)
	from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling

	type Invoice = SalesInvoice | PurchaseInvoice


class InvoiceItem(TypedDict):
	item_code: str
	qty: float
	rate: float
	price_list_rate: float


class BootStrapDevData(BootStrapTestMasterData):
	"""Set up transactions for development. Avoid using these transactions in test cases."""

	def make(self) -> Report:
		self.define_share_val()
		self.company_address = self.make_company_address()

		sales_invoices = self.make_sales_invoice()
		for invoice in sales_invoices:
			# Keep Vance Refrigeration as an unpaid sales invoice scenario.
			if invoice.customer == "Vance Refrigeration":
				continue
			payment_entry = self.make_payment_entry(invoice, invoice.posting_date)
			self.make_sales_withholding_tax_entry(invoice, payment_entry)

		purchase_invoices = self.make_purchase_invoice()
		purchase_entries = {}
		for invoice in purchase_invoices:
			# Keep one Aaron Grandy purchase invoice unpaid for payment-entry development.
			if invoice.bill_no == "AG-LEGAL-CONSULTING-UNPAID-001":
				continue
			payment_entry = self.make_payment_entry(invoice, invoice.posting_date)
			purchase_entries[invoice.bill_no] = self.make_purchase_withholding_tax_entry(payment_entry)

		two_months_ago = self.get_month_date(-2)
		period_key = getdate(two_months_ago).strftime("%Y-%m")
		self.make_pnd_filing(
			"Thai PND 3 Filing",
			two_months_ago,
			[purchase_entries[f"AG-LEGAL-CONSULTING-{period_key}"]],
		)
		self.make_pnd_filing(
			"Thai PND 53 Filing",
			two_months_ago,
			[purchase_entries[f"HPC-DELIVERY-SERVICE-{period_key}"]],
		)

		return self.report

	def make_company_address(self) -> str:
		if company_address := get_default_address("Company", self.company):
			self.record_change("skipped", "Address", company_address)
			return company_address

		address: "Address" = CompanyAddressFactory.create(
			address_title=self.company,
			branch_code="00000",
		)
		self.record_change("created", address.doctype, address.name)
		return address.name

	def make_sales_invoice(self) -> list["SalesInvoice"]:
		two_months_ago = self.get_month_date(-2)
		previous_month = self.get_month_date(-1)
		current_month = getdate(self.now)
		return [
			self.make_sales_invoice_record(
				customer="Dunmore High School",
				po_no="DM-MOCK-DUNMORE-PAPER-DELIVERY",
				posting_date=current_month,
				items=[
					self.invoice_item("DM-PREMIUM-COPY-PAPER", 10000),
					self.invoice_item("DELIVERY-SERVICE", 12000),
				],
			),
			self.make_sales_invoice_record(
				customer="Vance Refrigeration",
				po_no="DM-MOCK-VANCE-WAREHOUSE-RENT",
				posting_date=current_month,
				items=[self.invoice_item("WAREHOUSE-RENT", 12000)],
			),
			self.make_sales_invoice_record(
				customer="Lackawanna County",
				po_no=f"DM-MOCK-LACKAWANNA-DELIVERY-{two_months_ago:%Y-%m}",
				posting_date=two_months_ago,
				items=[self.invoice_item("DELIVERY-SERVICE", 18000)],
			),
			self.make_sales_invoice_record(
				customer="Mr. Deckert",
				po_no=f"DM-MOCK-DECKERT-WAREHOUSE-RENT-{previous_month:%Y-%m}",
				posting_date=previous_month,
				items=[self.invoice_item("WAREHOUSE-RENT", 14000)],
			),
			self.make_sales_invoice_record(
				customer="Phil Maguire",
				po_no=f"DM-MOCK-MAGUIRE-AUDIT-{current_month:%Y-%m}",
				posting_date=current_month,
				items=[self.invoice_item("AUDIT-FEE", 9000)],
			),
		]

	def make_purchase_invoice(self) -> list["PurchaseInvoice"]:
		two_months_ago = self.get_month_date(-2)
		previous_month = self.get_month_date(-1)
		current_month = getdate(self.now)
		return [
			self.make_purchase_invoice_record(
				supplier="Aaron Grandy",
				bill_no="AG-LEGAL-CONSULTING-UNPAID-001",
				posting_date=current_month,
				items=[self.invoice_item("LEGAL-CONSULTING-SERVICE", 5000)],
			),
			self.make_purchase_invoice_record(
				supplier="Aaron Grandy",
				bill_no="AG-LEGAL-CONSULTING-PAID-001",
				posting_date=current_month,
				items=[self.invoice_item("LEGAL-CONSULTING-SERVICE", 5000)],
			),
			self.make_purchase_invoice_record(
				supplier="Aaron Grandy",
				bill_no=f"AG-LEGAL-CONSULTING-{two_months_ago:%Y-%m}",
				posting_date=two_months_ago,
				items=[self.invoice_item("LEGAL-CONSULTING-SERVICE", 7500)],
			),
			self.make_purchase_invoice_record(
				supplier="Hammermill Paper Company",
				bill_no=f"HPC-DELIVERY-SERVICE-{two_months_ago:%Y-%m}",
				posting_date=two_months_ago,
				items=[self.invoice_item("DELIVERY-SERVICE", 18000)],
			),
			self.make_purchase_invoice_record(
				supplier="Aaron Grandy",
				bill_no=f"AG-AUDIT-FEE-{previous_month:%Y-%m}",
				posting_date=previous_month,
				items=[self.invoice_item("AUDIT-FEE", 9000)],
			),
			self.make_purchase_invoice_record(
				supplier="Serenity by Jan",
				bill_no=f"SBJ-WAREHOUSE-RENT-{previous_month:%Y-%m}",
				posting_date=previous_month,
				items=[self.invoice_item("WAREHOUSE-RENT", 24000)],
			),
			self.make_purchase_invoice_record(
				supplier="Athlead",
				bill_no=f"ATHLEAD-INSTALLATION-{current_month:%Y-%m}",
				posting_date=current_month,
				items=[self.invoice_item("INSTALLATION-SERVICE", 30000)],
			),
		]

	def make_sales_invoice_record(
		self,
		customer: str,
		po_no: str,
		posting_date: "DateTimeLikeObject",
		items: list[InvoiceItem],
	) -> "SalesInvoice":
		existing_names = frappe.get_all(
			"Sales Invoice",
			filters={"company": self.company, "po_no": po_no},
			pluck="name",
		)
		if len(existing_names) > 1:
			frappe.throw(_("Multiple Sales Invoices use development PO No. {0}.").format(frappe.bold(po_no)))
		if existing_names:
			invoice = frappe.get_doc("Sales Invoice", existing_names[0])
			if invoice.docstatus != 1 or invoice.customer != customer:
				frappe.throw(
					_("Development Sales Invoice {0} does not match the expected submitted record.").format(
						frappe.bold(invoice.name)
					)
				)
			self.record_change("skipped", invoice.doctype, invoice.name)
			return invoice

		invoice = SalesInvoiceFactory.create(
			customer=customer,
			po_no=po_no,
			set_posting_time=1,
			posting_date=posting_date,
			due_date=add_days(posting_date, 30),
			remarks=f"Dunder Mifflin mock invoice: {po_no}",
			items=items,
			submit=True,
		)
		self.record_change("created", invoice.doctype, invoice.name)
		return invoice

	def make_purchase_invoice_record(
		self,
		supplier: str,
		bill_no: str,
		posting_date: "DateTimeLikeObject",
		items: list[InvoiceItem],
	) -> "PurchaseInvoice":
		existing_names = frappe.get_all(
			"Purchase Invoice",
			filters={"company": self.company, "supplier": supplier, "bill_no": bill_no},
			pluck="name",
		)
		if len(existing_names) > 1:
			frappe.throw(
				_("Multiple Purchase Invoices use development Supplier Invoice No. {0}.").format(
					frappe.bold(bill_no)
				)
			)
		if existing_names:
			invoice = frappe.get_doc("Purchase Invoice", existing_names[0])
			if invoice.docstatus != 1 or invoice.supplier != supplier:
				frappe.throw(
					_(
						"Development Purchase Invoice {0} does not match the expected submitted record."
					).format(frappe.bold(invoice.name))
				)
			self.record_change("skipped", invoice.doctype, invoice.name)
			return invoice

		invoice = PurchaseInvoiceFactory.create(
			supplier=supplier,
			bill_no=bill_no,
			set_posting_time=1,
			bill_date=posting_date,
			posting_date=posting_date,
			due_date=add_days(posting_date, 30),
			remarks=f"Dunder Mifflin mock purchase: {bill_no}",
			items=items,
			submit=True,
		)
		self.record_change("created", invoice.doctype, invoice.name)
		return invoice

	def make_payment_entry(
		self,
		invoice: "Invoice",
		posting_date: "DateTimeLikeObject",
	) -> "PaymentEntry":
		reference_names = frappe.get_all(
			"Payment Entry Reference",
			filters={
				"reference_doctype": invoice.doctype,
				"reference_name": invoice.name,
			},
			pluck="parent",
		)
		active_names = (
			frappe.get_all(
				"Payment Entry",
				filters={"name": ["in", list(set(reference_names))], "docstatus": ["<", 2]},
				pluck="name",
			)
			if reference_names
			else []
		)
		if len(active_names) > 1:
			frappe.throw(
				_("Multiple active Payment Entries reference {0} {1}.").format(
					_(invoice.doctype), frappe.bold(invoice.name)
				)
			)
		if active_names:
			payment_entry = frappe.get_doc("Payment Entry", active_names[0])
			if payment_entry.docstatus != 1:
				frappe.throw(
					_("Development Payment Entry {0} must be submitted.").format(
						frappe.bold(payment_entry.name)
					)
				)
			self.record_change("skipped", payment_entry.doctype, payment_entry.name)
			return payment_entry

		payment_entry = get_payment_entry(
			invoice.doctype,
			invoice.name,
			bank_account=self.get_company_account("default_cash_account", "Asset", "Cash"),
			reference_date=posting_date,
		)
		payment_entry.set_posting_time = 1
		payment_entry.posting_date = posting_date
		payment_entry.reference_no = f"MOCK-{invoice.name}"
		payment_entry.reference_date = posting_date
		payment_entry.insert()
		payment_entry.submit()
		self.record_change("created", payment_entry.doctype, payment_entry.name)
		return payment_entry

	def make_purchase_withholding_tax_entry(
		self, payment_entry: "PaymentEntry"
	) -> "PurchaseWithholdingTaxEntry":
		existing_name = self.get_existing_withholding_tax_entry(
			payment_entry, "Purchase Withholding Tax Entry"
		)
		if existing_name:
			doc = frappe.get_doc("Purchase Withholding Tax Entry", existing_name)
			if not doc.pnd:
				doc = make_purchase_withholding_tax_entry(payment_entry.name, target_doc=doc)
				doc.db_set("pnd", doc.pnd)
				self.record_change("updated", doc.doctype, doc.name)
			else:
				self.record_change("skipped", doc.doctype, doc.name)
			return doc

		doc = make_purchase_withholding_tax_entry(payment_entry.name)
		doc.naming_series = "PWHT-.YYYY.-.#####"
		doc.insert()
		doc.submit()
		self.record_change("created", doc.doctype, doc.name)
		return doc

	def make_sales_withholding_tax_entry(
		self,
		invoice: "SalesInvoice",
		payment_entry: "PaymentEntry",
	) -> "SalesWithholdingTaxEntry":
		existing_name = self.get_existing_withholding_tax_entry(payment_entry, "Sales Withholding Tax Entry")
		if existing_name:
			doc = frappe.get_doc("Sales Withholding Tax Entry", existing_name)
			self.record_change("skipped", doc.doctype, doc.name)
			return doc

		certificate_number = f"SWHT-{invoice.po_no}"
		doc = make_sales_withholding_tax_entry(payment_entry.name)
		doc.naming_series = "SWHT-.YYYY.-.#####"
		doc.certificate_number = certificate_number
		doc.customer_address = doc.customer_address or invoice.customer_address
		doc.insert()

		certificate_content = (
			"MOCK THAI WITHHOLDING TAX CERTIFICATE\n"
			f"Certificate Number: {certificate_number}\n"
			f"Customer: {invoice.customer}\n"
			f"Payment Entry: {payment_entry.name}\n"
			f"Withholding Tax Base: THB {flt(doc.total_base_amount):,.2f}\n"
			f"Withholding Tax Amount: THB {flt(doc.total_tax_amount):,.2f}\n"
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
		self.record_change("created", doc.doctype, doc.name)
		return doc

	def make_pnd_filing(
		self,
		doctype: str,
		tax_period: "DateTimeLikeObject",
		sources: list["PurchaseWithholdingTaxEntry"],
	) -> "PNDFiling":
		tax_period = get_first_day(getdate(tax_period))
		existing_names = frappe.get_all(
			doctype,
			filters={
				"company": self.company,
				"tax_period": tax_period,
				"filing_type": "Normal",
				"additional_filing_no": 0,
				"docstatus": ["<", 2],
			},
			pluck="name",
		)
		if len(existing_names) > 1:
			frappe.throw(
				_("Multiple normal {0} records exist for tax period {1}.").format(
					_(doctype), frappe.bold(tax_period)
				)
			)
		if existing_names:
			filing = frappe.get_doc(doctype, existing_names[0])
			if filing.docstatus != 1:
				frappe.throw(_("Development filing {0} must be submitted.").format(frappe.bold(filing.name)))
			self.record_change("skipped", filing.doctype, filing.name)
			return filing

		filing = frappe.new_doc(doctype)
		filing.update(
			{
				"company": self.company,
				"company_address": self.company_address,
				"tax_period": tax_period,
				"filing_type": "Normal",
				"legal_basis": "Section 3 Tredecim",
				"filing_status": "Filed",
				"filed_date": add_days(add_months(tax_period, 1), 6),
				"filing_reference": f"MOCK-{doctype}-{tax_period:%Y-%m}",
				"filing_notes": "Development filing generated by bootstrap_dev_data.",
			}
		)
		for source in sources:
			filing = add_purchase_withholding_tax_entry_to_filing(source.name, filing)
		filing.insert()
		filing.submit()
		self.record_change("created", filing.doctype, filing.name)
		return filing

	def get_existing_withholding_tax_entry(
		self,
		payment_entry: "PaymentEntry",
		doctype: str,
	) -> str | None:
		parent_names = list(
			set(
				frappe.get_all(
					"Withholding Tax Entry Item",
					filters={
						"reference_doc_doctype": "Payment Entry",
						"reference_doc": payment_entry.name,
						"parenttype": doctype,
						"docstatus": ["<", 2],
					},
					pluck="parent",
				)
			)
		)
		if len(parent_names) > 1:
			frappe.throw(
				_("Multiple {0} records reference Payment Entry {1}.").format(
					_(doctype), frappe.bold(payment_entry.name)
				)
			)
		if not parent_names:
			return None

		docstatus = frappe.db.get_value(doctype, parent_names[0], "docstatus")
		if docstatus != 1:
			frappe.throw(
				_("Development {0} {1} must be submitted.").format(_(doctype), frappe.bold(parent_names[0]))
			)
		return parent_names[0]

	def get_month_date(self, month_offset: int) -> "DateTimeLikeObject":
		return add_days(get_first_day(add_months(self.now, month_offset)), 14)

	@staticmethod
	def invoice_item(item_code: str, rate: float) -> InvoiceItem:
		return {
			"item_code": item_code,
			"qty": 1,
			"rate": rate,
			"price_list_rate": rate,
		}
