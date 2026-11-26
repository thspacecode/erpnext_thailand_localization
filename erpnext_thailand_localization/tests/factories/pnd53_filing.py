from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.pnd53_filing.pnd53_filing import (
		PND53Filing,
	)


class PND53FilingFactory(DocTypeFactory["PND53Filing"]):
	doctype = "PND53 Filing"

	@classmethod
	def defaults(cls) -> "Json[PND53Filing]":
		return {"tax_period": "2026-08-19"}
