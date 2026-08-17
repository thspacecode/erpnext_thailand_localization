from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)


class SalesWithholdingTaxEntryFactory(DocTypeFactory["SalesWithholdingTaxEntry"]):
	doctype = "Sales Withholding Tax Entry"

	@classmethod
	def defaults(cls) -> "Json[SalesWithholdingTaxEntry]":
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
