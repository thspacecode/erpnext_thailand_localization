from typing import TYPE_CHECKING

from frappe.utils import add_days, getdate

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class SalesInvoiceFactory(DocTypeFactory["SalesInvoice"]):
	doctype = "Sales Invoice"

	@classmethod
	def defaults(cls) -> "Json[SalesInvoice]":
		posting_date = getdate()
		return {
			"company": "Dunder Mifflin",
			"customer": "Vance Refrigeration",
			"po_no": "TEST-SALES-INVOICE",
			"posting_date": posting_date,
			"due_date": add_days(posting_date, 30),
			"currency": "THB",
			"conversion_rate": 1,
			"remarks": "Dunder Mifflin mock invoice: TEST-SALES-INVOICE",
			"items": [
				{
					"item_code": "WAREHOUSE-RENT",
					"qty": 1,
					"rate": 12000,
					"price_list_rate": 12000,
				}
			],
		}
