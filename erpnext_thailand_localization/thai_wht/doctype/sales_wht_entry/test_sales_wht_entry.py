# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import SalesWHTEntryFactory
from erpnext_thailand_localization.thai_wht.model.t_withholding_tax_entry import (
	WithholdingTaxEntryTest,
)

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_wht.doctype.sales_wht_entry.sales_wht_entry import (
		SalesWHTEntry,
	)


class IntegrationTestSalesWHTEntry(WithholdingTaxEntryTest.TestCase):
	def get_base_doc(self) -> "SalesWHTEntry":
		return SalesWHTEntryFactory.build()
