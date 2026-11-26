# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import PND53FilingFactory
from erpnext_thailand_localization.thai_wht.model.t_pnd_filing import PNDFilingTest

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_wht.doctype.pnd53_filing.pnd53_filing import (
		PND53Filing,
	)


class IntegrationTestPND53Filing(PNDFilingTest.TestCase):
	def get_base_doc(self) -> "PND53Filing":
		return PND53FilingFactory.build()
