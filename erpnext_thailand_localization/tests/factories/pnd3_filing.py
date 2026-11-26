from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.doctype.pnd3_filing.pnd3_filing import (
		PND3Filing,
	)


class PND3FilingFactory(DocTypeFactory["PND3Filing"]):
	doctype = "PND3 Filing"

	@classmethod
	def defaults(cls) -> "Json[PND3Filing]":
		return {"tax_period": "2026-08-19"}
