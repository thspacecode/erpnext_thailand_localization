# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import ThaiPND53FilingFactory
from erpnext_thailand_localization.thai_withholding_tax.model.t_pnd_filing import PNDFilingTest

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing.thai_pnd_53_filing import (
		ThaiPND53Filing,
	)


class IntegrationTestThaiPND53Filing(PNDFilingTest.TestCase):
	def get_base_doc(self) -> "ThaiPND53Filing":
		return ThaiPND53FilingFactory.build()
