# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ThaiWithholdingTaxIncomeType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_withholding_tax_category_pnd.thai_withholding_tax_category_pnd import (
			ThaiWithholdingTaxCategoryPnd,
		)
		from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_withholding_tax_rate_by_category.thai_withholding_tax_rate_by_category import (
			ThaiWithholdingTaxRateByCategory,
		)

		default_thai_withholding_tax_rate: DF.Literal["", "0", "0.5", "0.75", "1", "2", "3", "5", "10", "15"]
		disabled: DF.Check
		income_type_name: DF.Data
		thai_withholding_tax_category_pnd: DF.Table[ThaiWithholdingTaxCategoryPnd]
		thai_withholding_tax_rate_by_category: DF.Table[ThaiWithholdingTaxRateByCategory]
	# end: auto-generated types

	pass
