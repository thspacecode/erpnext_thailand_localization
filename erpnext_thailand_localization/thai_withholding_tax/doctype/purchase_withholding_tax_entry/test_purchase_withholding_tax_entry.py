# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import (
	PurchaseWithholdingTaxEntryFactory,
)
from erpnext_thailand_localization.thai_withholding_tax.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
		PurchaseWithholdingTaxEntry,
	)


class IntegrationTestPurchaseWithholdingTaxEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> "PurchaseWithholdingTaxEntry":
		return PurchaseWithholdingTaxEntryFactory.build(
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
