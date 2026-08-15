# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import ThaiPND3FilingFactory
from erpnext_thailand_localization.thai_withholding_tax.model.t_pnd_filing import PNDFilingTest

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing.thai_pnd_3_filing import (
		ThaiPND3Filing,
	)


class IntegrationTestThaiPND3Filing(PNDFilingTest.TestCase):
	def get_base_doc(self) -> "ThaiPND3Filing":
		return ThaiPND3FilingFactory.build()
