# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

from erpnext_thailand_localization.thai_withholding_tax.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)


class IntegrationTestPurchaseWithholdingTaxEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> Document:
		return frappe.get_doc(
			{
				"doctype": "Purchase Withholding Tax Entry",
				"company_currency": "THB",
				"supplier": "Hammermill Paper Company",
				"supplier_address": "Hammermill Paper Company-Billing",
				"items": [
					{
						"income_type": "Service",
						"base_amount": 1000,
						"tax_rate": 3,
						"tax_amount": 30,
					}
				],
			}
		)
