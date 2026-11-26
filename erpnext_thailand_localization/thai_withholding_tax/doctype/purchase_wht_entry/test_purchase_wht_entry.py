# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import (
	PurchaseWHTEntryFactory,
)
from erpnext_thailand_localization.thai_withholding_tax.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_wht_entry.purchase_wht_entry import (
		PurchaseWHTEntry,
	)


class IntegrationTestPurchaseWHTEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> "PurchaseWHTEntry":
		return PurchaseWHTEntryFactory.build(
			supplier="Hammermill Paper Company",
			supplier_address="Hammermill Paper Company-Billing",
			items=[
				{
					"income_type": "Service",
					"base_amount": 1000,
					"tax_rate": 3,
					"tax_amount": 30,
				}
			],
		)
