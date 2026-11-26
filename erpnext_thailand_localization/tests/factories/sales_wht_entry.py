from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_wht.doctype.sales_wht_entry.sales_wht_entry import (
		SalesWHTEntry,
	)


class SalesWHTEntryFactory(DocTypeFactory["SalesWHTEntry"]):
	doctype = "Sales WHT Entry"

	@classmethod
	def defaults(cls) -> "Json[SalesWHTEntry]":
		return {
			"company": "Dunder Mifflin",
			"company_currency": "THB",
			"customer": "Lackawanna County",
			"customer_address": "Lackawanna County-Billing",
			"items": [
				{
					"income_type": "Service",
					"base_amount": 1000,
					"tax_rate": 3,
					"tax_amount": 30,
				}
			],
		}
