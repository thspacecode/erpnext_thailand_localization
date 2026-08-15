# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling


class ThaiPND53Filing(PNDFiling):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing_item.thai_pnd_53_filing_item import (
			ThaiPND53FilingItem,
		)

		additional_filing_no: DF.Int
		amended_from: DF.Link | None
		attachment_format: DF.Literal["Paper", "Computer Media"]
		attachment_page_count: DF.Int
		authorized_signatory: DF.Link | None
		company: DF.Link
		company_address: DF.Link
		company_address_line1: DF.Data | None
		company_address_line2: DF.Data | None
		company_branch_code: DF.Data
		company_country: DF.Link | None
		company_currency: DF.Link
		company_district: DF.Data | None
		company_name: DF.Data
		company_postal_code: DF.Data | None
		company_province: DF.Data | None
		company_subdistrict: DF.Data | None
		company_tax_id: DF.Data
		declaration_date: DF.Date
		filed_date: DF.Date | None
		filing_notes: DF.SmallText | None
		filing_receipt: DF.Attach | None
		filing_reference: DF.Data | None
		filing_status: DF.Literal["Prepared", "Filed", "Accepted", "Rejected"]
		filing_type: DF.Literal["Normal", "Additional"]
		grand_total: DF.Currency
		items: DF.Table[ThaiPND53FilingItem]
		legal_basis: DF.Literal["Section 3 Tredecim", "Section 65 Quater", "Section 69 Bis"]
		naming_series: DF.Literal["PND53-.YYYY.-.#####"]
		recipient_count: DF.Int
		signatory_name: DF.Data | None
		signatory_position: DF.Data | None
		signature_image: DF.AttachImage | None
		surcharge_amount: DF.Currency
		tax_period: DF.Date
		total_base_amount: DF.Currency
		total_tax_amount: DF.Currency
	# end: auto-generated types

	pnd_type = "PND 53"
	item_doctype = "Thai PND 53 Filing Item"
	legal_bases = ("Section 3 Tredecim", "Section 65 Quater", "Section 69 Bis")
