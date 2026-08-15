from typing import TYPE_CHECKING

from frappe.utils import add_days, getdate

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class PurchaseInvoiceFactory(DocTypeFactory["PurchaseInvoice"]):
	doctype = "Purchase Invoice"

	@classmethod
	def defaults(cls) -> "Json[PurchaseInvoice]":
		posting_date = getdate()
		return {
			"company": "Dunder Mifflin",
			"supplier": "Aaron Grandy",
			"bill_no": "TEST-PURCHASE-INVOICE",
			"bill_date": posting_date,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, 30),
			"currency": "THB",
			"conversion_rate": 1,
			"remarks": "Dunder Mifflin mock purchase: TEST-PURCHASE-INVOICE",
			"items": [
				{
					"item_code": "LEGAL-CONSULTING-SERVICE",
					"qty": 1,
					"rate": 5000,
					"price_list_rate": 5000,
				}
			],
		}
