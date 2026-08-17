# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import SalesWithholdingTaxEntryFactory
from erpnext_thailand_localization.thai_withholding_tax.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
		SalesWithholdingTaxEntry,
	)


class IntegrationTestSalesWithholdingTaxEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> "SalesWithholdingTaxEntry":
		return SalesWithholdingTaxEntryFactory.build()
