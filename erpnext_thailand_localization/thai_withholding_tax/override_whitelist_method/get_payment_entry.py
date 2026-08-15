from typing import TYPE_CHECKING

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry as erpnext_get_payment_entry,
)

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
	from frappe.utils import DateTimeLikeObject

from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	apply_thai_withholding_tax,
)


@frappe.whitelist()
def get_payment_entry(
	dt: str,
	dn: str,
	party_amount: float | None = None,
	bank_account: str | None = None,
	bank_amount: float | None = None,
	party_type: str | None = None,
	payment_type: str | None = None,
	reference_date: "DateTimeLikeObject | None" = None,
	created_from_payment_request: bool = False,
) -> "PaymentEntry":
	payment_entry = erpnext_get_payment_entry(
		dt=dt,
		dn=dn,
		party_amount=party_amount,
		bank_account=bank_account,
		bank_amount=bank_amount,
		party_type=party_type,
		payment_type=payment_type,
		reference_date=reference_date,
		created_from_payment_request=created_from_payment_request,
	)

	if dt not in ("Sales Invoice", "Sales Order", "Purchase Invoice", "Purchase Order"):
		return payment_entry

	reference_document = frappe.get_doc(dt, dn)
	reference_document.check_permission("read")
	if not reference_document.get("is_return"):
		apply_thai_withholding_tax(payment_entry, reference_document)

	return payment_entry
