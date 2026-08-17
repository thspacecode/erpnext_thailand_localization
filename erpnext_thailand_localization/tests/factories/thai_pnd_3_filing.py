from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing.thai_pnd_3_filing import (
		ThaiPND3Filing,
	)


class ThaiPND3FilingFactory(DocTypeFactory["ThaiPND3Filing"]):
	doctype = "Thai PND 3 Filing"

	@classmethod
	def defaults(cls) -> "Json[ThaiPND3Filing]":
		return {"tax_period": "2026-08-19"}
