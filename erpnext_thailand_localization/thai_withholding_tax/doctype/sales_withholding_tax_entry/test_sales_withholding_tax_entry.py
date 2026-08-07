# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document

from erpnext_thailand_localization.thai_withholding_tax.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)


class IntegrationTestSalesWithholdingTaxEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> Document:
		return frappe.get_doc(
			{
				"doctype": "Sales Withholding Tax Entry",
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
		)
