import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_thailand_localization.thai_value_added_tax.service.undue_value_added_tax import (
	fetch_undue_vat_detail,
)


def validate_undue_vat_items(doc: Document, method: str | None = None) -> None:
	"""Require every invoice Item to allow the applicable undue VAT direction."""
	if doc.doctype not in ("Sales Invoice", "Purchase Invoice"):
		return

	direction = "sales" if doc.doctype == "Sales Invoice" else "purchase"
	company = frappe.get_cached_doc("Company", doc.company)
	templates = {
		row.tax_template for row in company.get(f"custom_undue_{direction}_value_added_tax_templates") or []
	}
	account = company.get(f"undue_{direction}_value_added_tax_account")
	uses_undue_account = account and any(row.account_head == account for row in doc.get("taxes") or [])
	if doc.get("taxes_and_charges") not in templates and not uses_undue_account:
		return

	for row in doc.get("items") or []:
		if not row.item_code:
			frappe.throw(_("Row {0}: Select an Item to validate undue VAT eligibility.").format(row.idx))
		if not fetch_undue_vat_detail(row.item_code)[f"allow_{direction}"]:
			frappe.throw(
				_("Row {0}: Item {1} does not allow undue {2} VAT.").format(row.idx, row.item_code, direction)
			)
