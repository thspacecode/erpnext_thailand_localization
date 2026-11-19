import frappe
from frappe import _
from frappe.utils import flt, getdate

from erpnext_thailand_localization.thai_value_added_tax.service.vat_conversion import (
	get_undue_vat_conversion_entry,
)
from erpnext_thailand_localization.thai_value_added_tax.service.vat_entry import (
	cancel_entries,
	create_entries,
)


def convert_purchase_vat(doc, method=None):
	"""Recognize purchase undue VAT once, in the invoice save transaction."""
	if doc.docstatus != 1:
		return
	stored = frappe.get_doc("Purchase Invoice", doc.name, for_update=True)
	conversion = stored.get("custom_purchase_vat_conversion")
	previous = doc.get_doc_before_save()
	if conversion:
		if previous and (
			doc.bill_no != previous.bill_no or getdate(doc.bill_date) != getdate(previous.bill_date)
		):
			frappe.throw(_("Cancel and amend the Purchase Invoice to change recognized tax invoice details."))
		return
	company = frappe.get_cached_doc("Company", doc.company)
	account = company.get("undue_purchase_value_added_tax_account")
	taxes = [row for row in doc.taxes if account and row.account_head == account]
	if not taxes or not doc.bill_no:
		return
	if not doc.bill_date:
		frappe.throw(_("Supplier Invoice Date is required to convert purchase undue VAT."))

	rows = get_purchase_vat_rows(doc, taxes)
	if not rows:
		return
	payload = get_undue_vat_conversion_entry(doc)
	payload["posting_date"] = doc.bill_date
	journal = frappe.get_doc(payload).insert()
	journal.submit()
	create_entries(doc, rows)
	doc.db_set("custom_purchase_vat_conversion", journal.name, update_modified=False)


def get_purchase_vat_rows(doc, taxes):
	"""Use final company-currency amounts for supported net-total purchase VAT rows."""
	rows = []
	for tax in taxes:
		if not flt(tax.base_tax_amount_after_discount_amount):
			continue
		if (
			tax.charge_type != "On Net Total"
			or tax.category != "Total"
			or tax.add_deduct_tax != "Add"
			or flt(tax.rate) <= 0
		):
			frappe.throw(_("Purchase VAT conversion requires added On Net Total VAT in the Total category."))
		base = flt(doc.base_net_total)
		if flt(tax.base_tax_amount):
			base *= flt(tax.base_tax_amount_after_discount_amount) / flt(tax.base_tax_amount)
		amount = flt(tax.base_tax_amount_after_discount_amount)
		if abs(flt(base * flt(tax.rate) / 100, 2) - amount) > 0.02:
			frappe.throw(_("Purchase VAT conversion requires a uniform VAT rate on the invoice net total."))
		rows.append(
			{
				"direction": "Purchase",
				"party": doc.supplier,
				"tax_invoice_number": doc.bill_no,
				"tax_invoice_date": doc.bill_date,
				"report_date": doc.bill_date,
				"vat_category": "Taxable",
				"rate": tax.rate,
				"tax_base": flt(base, 2),
				"tax_amount": amount,
				"source_identity": tax.name,
			}
		)
	return rows


def cancel_purchase_vat(doc, method=None):
	"""Respect PP30 locks and reverse generated records in the caller transaction."""
	cancel_entries(doc)
	conversion = frappe.db.get_value("Purchase Invoice", doc.name, "custom_purchase_vat_conversion")
	if conversion:
		journal = frappe.get_doc("Journal Entry", conversion)
		doc.db_set("custom_purchase_vat_conversion", None, update_modified=False)
		if journal.docstatus == 1:
			journal.cancel()


def validate_conversion_link(doc, method=None):
	"""Only conversion code can set or clear the generated journal link."""
	previous = doc.get_doc_before_save()
	expected = previous.get("custom_purchase_vat_conversion") if previous else None
	if (doc.get("custom_purchase_vat_conversion") or None) != (expected or None):
		frappe.throw(_("Purchase VAT Conversion is managed by the conversion workflow."))


def validate_conversion_cancellation(doc, method=None):
	"""Require invoice cancellation so the VAT register and GL stay in sync."""
	if frappe.db.exists("Purchase Invoice", {"custom_purchase_vat_conversion": doc.name, "docstatus": 1}):
		frappe.throw(_("Cancel the source Purchase Invoice to cancel its VAT conversion."))
