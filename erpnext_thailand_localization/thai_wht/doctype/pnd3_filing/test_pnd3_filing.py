# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

from typing import TYPE_CHECKING

from erpnext_thailand_localization.tests.factories import PND3FilingFactory
from erpnext_thailand_localization.thai_wht.model.t_pnd_filing import PNDFilingTest

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_wht.doctype.pnd3_filing.pnd3_filing import (
		PND3Filing,
	)


class IntegrationTestPND3Filing(PNDFilingTest.TestCase):
	def get_base_doc(self) -> "PND3Filing":
		return PND3FilingFactory.build()
