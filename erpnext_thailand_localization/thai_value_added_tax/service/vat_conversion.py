import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext_thailand_localization.doc_events.invoice import validate_undue_vat_items


def get_undue_vat_conversion_entry(
	invoice: Document, conversion_ratio: float = 1, precision: int = 2
) -> dict:
	"""Return an unsaved Journal Entry payload for the allocated share of undue VAT."""
	if not 0 < conversion_ratio <= 1:
		frappe.throw(_("VAT conversion ratio must be greater than zero and at most one."))
	if invoice.doctype not in ("Sales Invoice", "Purchase Invoice"):
		frappe.throw(_("Expected a Sales Invoice or Purchase Invoice."))
	validate_undue_vat_items(invoice)
	direction = "sales" if invoice.doctype == "Sales Invoice" else "purchase"
	company = frappe.get_cached_doc("Company", invoice.company)
	undue_account = company.get(f"undue_{direction}_value_added_tax_account")
	vat_account = company.get(f"{direction}_value_added_tax_account")
	if not undue_account or not vat_account:
		frappe.throw(_("Set both undue VAT and VAT accounts in Company {0}.").format(invoice.company))
	if undue_account == vat_account:
		frappe.throw(_("Undue VAT and VAT accounts must be different."))

	for name in (undue_account, vat_account):
		account = frappe.get_cached_doc("Account", name)
		if account.company != invoice.company or account.is_group or account.disabled:
			frappe.throw(_("VAT conversion requires active ledger accounts in the invoice Company."))
		if account.account_currency != company.default_currency:
			frappe.throw(_("VAT conversion accounts must use the Company currency."))

	accounts = []
	for tax in invoice.get("taxes") or []:
		if tax.account_head != undue_account:
			continue
		amount = flt(flt(tax.base_tax_amount_after_discount_amount) * conversion_ratio, precision)
		if direction == "purchase" and tax.get("add_deduct_tax") == "Deduct":
			amount = -amount
		if not amount:
			continue
		debit = amount if direction == "sales" else -amount
		for name, signed_debit in ((undue_account, debit), (vat_account, -debit)):
			accounts.append(
				{
					"account": name,
					"account_currency": company.default_currency,
					"exchange_rate": 1,
					"debit_in_account_currency": max(signed_debit, 0),
					"credit_in_account_currency": max(-signed_debit, 0),
					"cost_center": tax.get("cost_center") or invoice.get("cost_center"),
				}
			)
	if not accounts:
		frappe.throw(_("The invoice has no non-zero undue VAT tax rows to convert."))

	return {
		"doctype": "Journal Entry",
		"voucher_type": "Journal Entry",
		"company": invoice.company,
		"posting_date": invoice.posting_date,
		"user_remark": _("Undue VAT conversion for {0} {1}").format(invoice.doctype, invoice.name),
		"accounts": accounts,
	}
