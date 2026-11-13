# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

from erpnext_thailand_localization.controllers.vat_entry import VATEntry


class SalesVATEntry(VATEntry):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		amended_from: DF.Link | None
		branch_code: DF.Data | None
		company: DF.Link
		company_address_display: DF.SmallText | None
		company_branch_code: DF.Data | None
		company_currency: DF.Link | None
		company_tax_address: DF.Link | None
		company_tax_id: DF.Data | None
		company_taxpayer_name: DF.Data | None
		generation_key: DF.Data | None
		gl_entry: DF.Link | None
		naming_series: DF.Literal["SVAT-.YYYY.-.#####"]
		party: DF.Link
		party_name: DF.Data | None
		remarks: DF.SmallText | None
		report_date: DF.Date | None
		source_identity: DF.Data | None
		tax_amount: DF.Currency
		tax_base: DF.Currency
		tax_id: DF.Data | None
		tax_invoice_attachment: DF.Attach | None
		tax_invoice_book: DF.Data | None
		tax_invoice_date: DF.Date | None
		tax_invoice_number: DF.Data | None
		tax_rate: DF.Percent
		vat_category: DF.Literal["Taxable", "Zero Rated", "Exempt"]
		voucher_no: DF.DynamicLink
		voucher_type: DF.Link
	# end: auto-generated types

	party_type = "Customer"
	direction = "sales"
