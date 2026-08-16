from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)


class PurchaseWithholdingTaxEntryFactory(DocTypeFactory["PurchaseWithholdingTaxEntry"]):
	doctype = "Purchase Withholding Tax Entry"

	@classmethod
	def defaults(cls) -> "Json[PurchaseWithholdingTaxEntry]":
		return {
			"company": "Dunder Mifflin",
			"company_currency": "THB",
			"payment_date": "2026-08-15",
			"pnd": "PND 3",
			"supplier": "Aaron Grandy",
			"supplier_address": "Aaron Grandy-Billing",
			"items": [
				{
					"income_type": "6 เงินได้จากวิชาชีพอิสระ",
					"base_amount": 1000,
					"tax_rate": 3,
					"tax_amount": 30,
				}
			],
		}
