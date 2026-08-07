# Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext_thailand_localization.thai_withholding_tax.model.withholding_tax_entry import (
	WithholdingTaxEntry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.payment_entry import (
	make_withholding_tax_entry,
)


class SalesWithholdingTaxEntry(WithholdingTaxEntry):
	party_type = "Customer"
	party_field = "customer"
	address_field = "customer_address"

	def validate(self):
		if self.certificate_number:
			self.certificate_number = self.certificate_number.strip()
		self.validate_certificate()
		super().validate()

	def validate_certificate(self):
		if self.docstatus == 1 and not self.certificate_number:
			frappe.throw(_("Certificate Number is required before submission."))
		if self.docstatus == 1 and not self.certificate_attachment:
			frappe.throw(_("Certificate Attachment is required before submission."))
		if not self.certificate_number:
			return

		duplicate = frappe.db.exists(
			"Sales Withholding Tax Entry",
			{
				"company": self.company,
				"customer": self.customer,
				"certificate_number": self.certificate_number,
				"docstatus": ["!=", 2],
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Certificate Number {0} already exists for this Company and Customer in {1}.").format(
					frappe.bold(self.certificate_number), frappe.bold(duplicate)
				)
			)


@frappe.whitelist()
def make_sales_withholding_tax_entry(source_name, target_doc=None, kwargs=None):
	return make_withholding_tax_entry(
		source_name=source_name,
		target_doctype="Sales Withholding Tax Entry",
		payment_type="Receive",
		party_type="Customer",
		party_field="customer",
		address_field="customer_address",
		target_doc=target_doc,
	)
