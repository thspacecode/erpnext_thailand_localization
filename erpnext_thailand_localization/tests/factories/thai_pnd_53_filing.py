from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing.thai_pnd_53_filing import (
		ThaiPND53Filing,
	)


class ThaiPND53FilingFactory(DocTypeFactory["ThaiPND53Filing"]):
	doctype = "Thai PND 53 Filing"

	@classmethod
	def defaults(cls) -> "Json[ThaiPND53Filing]":
		return {"tax_period": "2026-08-19"}
