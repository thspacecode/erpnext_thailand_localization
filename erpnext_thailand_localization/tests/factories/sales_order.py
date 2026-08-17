from typing import TYPE_CHECKING

from frappe.utils import add_days, getdate

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class SalesOrderFactory(DocTypeFactory["SalesOrder"]):
	doctype = "Sales Order"

	@classmethod
	def defaults(cls) -> "Json[SalesOrder]":
		transaction_date = getdate()
		return {
			"company": "Dunder Mifflin",
			"customer": "Vance Refrigeration",
			"transaction_date": transaction_date,
			"delivery_date": add_days(transaction_date, 1),
			"currency": "THB",
			"conversion_rate": 1,
			"items": [{"item_code": "WAREHOUSE-RENT", "qty": 1, "rate": 12000}],
		}
