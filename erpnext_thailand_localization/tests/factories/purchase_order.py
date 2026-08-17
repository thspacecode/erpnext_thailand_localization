from typing import TYPE_CHECKING

from frappe.utils import add_days, getdate

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder


class PurchaseOrderFactory(DocTypeFactory["PurchaseOrder"]):
	doctype = "Purchase Order"

	@classmethod
	def defaults(cls) -> "Json[PurchaseOrder]":
		transaction_date = getdate()
		return {
			"company": "Dunder Mifflin",
			"supplier": "Aaron Grandy",
			"transaction_date": transaction_date,
			"schedule_date": add_days(transaction_date, 1),
			"currency": "THB",
			"conversion_rate": 1,
			"items": [{"item_code": "LEGAL-CONSULTING-SERVICE", "qty": 1, "rate": 5000}],
		}
