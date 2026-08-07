import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


def make_withholding_tax_entry(
	source_name: str,
	target_doctype: str,
	payment_type: str,
	party_type: str,
	party_field: str,
	address_field: str,
	target_doc=None,
):
	source = frappe.get_doc("Payment Entry", source_name)
	source.check_permission("read")

	if source.docstatus != 1:
		frappe.throw(_("Payment Entry {0} must be submitted.").format(frappe.bold(source_name)))
	if source.payment_type != payment_type or source.party_type != party_type:
		frappe.throw(
			_("Payment Entry {0} is not eligible to create a {1}.").format(
				frappe.bold(source_name), _(target_doctype)
			)
		)
	if not frappe.has_permission(target_doctype, "create"):
		frappe.throw(
			_("You do not have permission to create a {0}.").format(_(target_doctype)), frappe.PermissionError
		)

	has_existing_target = bool(target_doc)
	party_doc = frappe.get_doc(party_type, source.party)
	party_doc.check_permission("read")
	party_address_field = f"{frappe.scrub(party_type)}_primary_address"
	party_address = party_doc.get(party_address_field)
	if party_address:
		frappe.get_doc("Address", party_address).check_permission("read")

	company_doc = frappe.get_doc("Company", source.company)
	company_doc.check_permission("read")
	company_currency = company_doc.default_currency

	def set_target_values(source_doc, target):
		values = {
			"company": source_doc.company,
			"company_currency": company_currency,
			"payment_date": source_doc.posting_date,
			party_field: source_doc.party,
			address_field: party_address,
		}
		for fieldname, value in values.items():
			if not has_existing_target or not target.get(fieldname):
				target.set(fieldname, value)

	return get_mapped_doc(
		"Payment Entry",
		source_name,
		{
			"Payment Entry": {
				"doctype": target_doctype,
				"field_no_map": ["company", "company_currency"],
			}
		},
		target_doc,
		set_target_values,
	)
