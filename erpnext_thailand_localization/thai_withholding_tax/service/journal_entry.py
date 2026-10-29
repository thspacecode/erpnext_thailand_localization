from typing import TYPE_CHECKING

import frappe
from erpnext.accounts.party import get_party_account
from frappe import _
from frappe.utils import flt, today

if TYPE_CHECKING:
	from erpnext.accounts.doctype.journal_entry.journal_entry import JournalEntry

	from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling


def add_pnd_filing_to_journal_entry(
	filing_doctype: str,
	source_name: str,
	target_doc: "str | JournalEntry | None" = None,
) -> "JournalEntry":
	if filing_doctype == "Thai PND 3 Filing":
		account_field = "purchase_withholding_tax_pnd3_account"
	elif filing_doctype == "Thai PND 53 Filing":
		account_field = "purchase_withholding_tax_pnd53_account"
	else:
		frappe.throw(_("Unsupported PND filing type."))

	filing: "PNDFiling" = frappe.get_doc(filing_doctype, source_name)
	filing.check_permission("read")
	if filing.docstatus != 1:
		frappe.throw(_("PND Filing {0} must be submitted.").format(frappe.bold(source_name)))

	journal_entry = get_target_journal_entry(target_doc)
	journal_entry.check_permission("create" if journal_entry.is_new() else "write")
	validate_target_company(journal_entry, filing)
	validate_reference(journal_entry, filing)
	remove_empty_account_rows(journal_entry)

	company = frappe.get_cached_doc("Company", filing.company)
	withholding_account = company.get(account_field)
	if not withholding_account:
		frappe.throw(
			_("Please set {0} in Company {1}.").format(
				frappe.bold(_(company.meta.get_label(account_field))),
				frappe.bold(filing.company),
			)
		)
	validate_company_account(withholding_account, filing.company)

	revenue_department = frappe.db.get_single_value("Thai Localization Settings", "revenue_department")
	if not revenue_department:
		frappe.throw(
			_("Please set Revenue Department in Thai Localization Settings."),
			title=_("Thai Localization Settings Required"),
		)
	if not frappe.db.exists("Supplier", {"name": revenue_department, "disabled": 0}):
		frappe.throw(
			_("Revenue Department Supplier {0} must be enabled.").format(frappe.bold(revenue_department))
		)
	payable_account = get_party_account("Supplier", revenue_department, filing.company)
	validate_company_account(payable_account, filing.company)

	if not journal_entry.company:
		journal_entry.company = filing.company
	if not journal_entry.accounts:
		journal_entry.posting_date = filing.filed_date or today()
	journal_entry.custom_reference_doctype = filing.doctype
	journal_entry.custom_reference_doc = filing.name

	journal_entry.append(
		"accounts",
		{
			"account": withholding_account,
			"account_currency": filing.currency,
			"exchange_rate": 1,
			"debit_in_account_currency": filing.total_tax_amount,
			"user_remark": _("Withholding tax payable from {0} {1}").format(_(filing.pnd_type), filing.name),
		},
	)

	if flt(filing.surcharge_amount):
		journal_entry.append(
			"accounts",
			{
				"account_currency": filing.currency,
				"exchange_rate": 1,
				"debit_in_account_currency": filing.surcharge_amount,
				"user_remark": _("Select the expense account for the surcharge on {0}.").format(filing.name),
			},
		)

	journal_entry.append(
		"accounts",
		{
			"account": payable_account,
			"account_currency": filing.currency,
			"party_type": "Supplier",
			"party": revenue_department,
			"exchange_rate": 1,
			"credit_in_account_currency": filing.grand_total,
			"is_advance": "No",
			"user_remark": _("Amount payable to the Revenue Department for {0} {1}").format(
				_(filing.pnd_type), filing.name
			),
		},
	)

	journal_entry.custom_remark = 1
	filing_remark = _("Revenue Department payable for {0} filing {1}").format(_(filing.pnd_type), filing.name)
	journal_entry.remark = "\n".join(filter(None, (journal_entry.remark, filing_remark)))
	journal_entry.set_amounts_in_company_currency()
	journal_entry.set_total_debit_credit()
	return journal_entry


def get_target_journal_entry(target_doc: "str | JournalEntry | None") -> "JournalEntry":
	if isinstance(target_doc, str):
		return frappe.get_doc(frappe.parse_json(target_doc))
	if target_doc:
		return target_doc
	return frappe.new_doc("Journal Entry")


def remove_empty_account_rows(journal_entry: "JournalEntry") -> None:
	meaningful_fields = (
		"account",
		"party_type",
		"party",
		"bank_account",
		"reference_type",
		"reference_name",
		"advance_voucher_type",
		"advance_voucher_no",
		"user_remark",
		"debit_in_account_currency",
		"credit_in_account_currency",
		"debit",
		"credit",
	)
	for account_row in list(journal_entry.accounts):
		if not any(account_row.get(fieldname) for fieldname in meaningful_fields):
			journal_entry.remove(account_row)


def validate_target_company(journal_entry: "JournalEntry", filing: "PNDFiling") -> None:
	if journal_entry.company and journal_entry.company != filing.company:
		frappe.throw(
			_("Journal Entry company must match PND Filing company {0}.").format(frappe.bold(filing.company))
		)


def validate_reference(journal_entry: "JournalEntry", filing: "PNDFiling") -> None:
	if journal_entry.custom_reference_doctype or journal_entry.custom_reference_doc:
		if (
			journal_entry.custom_reference_doctype == filing.doctype
			and journal_entry.custom_reference_doc == filing.name
		):
			frappe.throw(_("PND Filing {0} has already been added.").format(frappe.bold(filing.name)))
		frappe.throw(_("A Journal Entry can reference only one PND Filing."))

	existing_journal_entry = frappe.db.get_value(
		"Journal Entry",
		{
			"custom_reference_doctype": filing.doctype,
			"custom_reference_doc": filing.name,
			"docstatus": ["<", 2],
		},
		"name",
	)
	if existing_journal_entry:
		frappe.throw(
			_("PND Filing {0} is already linked to Journal Entry {1}.").format(
				frappe.bold(filing.name), frappe.bold(existing_journal_entry)
			)
		)


def validate_company_account(account: str, company: str) -> None:
	account_details = frappe.get_cached_value("Account", account, ["company", "is_group"], as_dict=True)
	if not account_details or account_details.company != company or account_details.is_group:
		frappe.throw(
			_("Account {0} must be a ledger account for Company {1}.").format(
				frappe.bold(account), frappe.bold(company)
			)
		)
