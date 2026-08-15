from typing import TYPE_CHECKING

import frappe
from frappe.utils import getdate

from erpnext_thailand_localization.tests.factories import (
	PurchaseWithholdingTaxEntryFactory,
)
from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing import (
	get_eligible_items,
	get_income_type_pnd,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)


class TestPNDFiling(ERPNextThaiTestSuite):
	company = "Dunder Mifflin"
	income_type = "6 เงินได้จากวิชาชีพอิสระ"

	@staticmethod
	def create_source(
		supplier: str,
		supplier_address: str,
		payment_date: str = "2099-08-15",
		submit: bool = True,
	) -> "PurchaseWithholdingTaxEntry":
		return PurchaseWithholdingTaxEntryFactory.create(
			supplier=supplier,
			supplier_address=supplier_address,
			payment_date=payment_date,
			submit=submit,
		)

	def test_get_income_type_pnd(self) -> None:
		for income_type, category, expected in (
			(None, "Individual - Domestic", None),
			(self.income_type, None, None),
			(self.income_type, "Individual - Domestic", "PND 3"),
			(self.income_type, "Juristic Person - Domestic", "PND 53"),
			(self.income_type, "Unmapped Category", None),
		):
			with self.subTest(income_type=income_type, category=category):
				self.assertEqual(get_income_type_pnd(income_type, category), expected)

	def test_get_eligible_items(self) -> None:
		pnd3_source = self.create_source("Aaron Grandy", "Aaron Grandy-Billing")
		pnd53_source = self.create_source("Hammermill Paper Company", "Hammermill Paper Company-Billing")
		self.create_source("Aaron Grandy", "Aaron Grandy-Billing", payment_date="2099-07-31")
		self.create_source("Aaron Grandy", "Aaron Grandy-Billing", submit=False)

		for filing_doctype, source in (
			("Thai PND 3 Filing", pnd3_source),
			("Thai PND 53 Filing", pnd53_source),
		):
			with self.subTest(filing_doctype=filing_doctype):
				self.assertEqual(
					get_eligible_items(filing_doctype, self.company, "2099-08-27"),
					[
						{
							"purchase_withholding_tax_entry": source.name,
							"withholding_tax_entry_item": source.items[0].name,
							"payment_date": getdate("2099-08-15"),
							"supplier": source.supplier,
							"supplier_address": source.supplier_address,
							"income_type": self.income_type,
							"base_amount": 1000,
							"tax_rate": 3,
							"tax_amount": 30,
						}
					],
				)

		frappe.get_doc(
			{
				"doctype": "Thai PND 3 Filing Item",
				"parent": "TEST-PND-3-FILING",
				"parenttype": "Thai PND 3 Filing",
				"parentfield": "items",
				"docstatus": 1,
				"purchase_withholding_tax_entry": pnd3_source.name,
				"withholding_tax_entry_item": pnd3_source.items[0].name,
			}
		).db_insert()

		with self.subTest("exclude items already included in a submitted filing"):
			self.assertEqual(get_eligible_items("Thai PND 3 Filing", self.company, "2099-08-01"), [])

	def test_get_eligible_items_validates_filing_type_and_permission(self) -> None:
		with self.subTest("unsupported filing type"):
			with self.assertRaisesRegex(frappe.ValidationError, "Unsupported PND filing type"):
				get_eligible_items("Purchase Withholding Tax Entry", self.company, "2099-08-01")

		with self.subTest("create permission is required"):
			with self.set_create_user():
				with self.assertRaises(frappe.PermissionError):
					get_eligible_items("Thai PND 3 Filing", self.company, "2099-08-01")
