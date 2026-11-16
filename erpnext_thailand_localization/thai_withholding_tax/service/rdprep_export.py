"""Generate mapped recipient text for RDPrep 1.3.2, not an electronic tax return."""

import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

if TYPE_CHECKING:
	from erpnext_thailand_localization.thai_withholding_tax.model.pnd_filing import PNDFiling


@frappe.whitelist()
def download_rdprep(doctype: str, name: str) -> None:
	"""Download stored, submitted snapshots after checking read permission."""
	if doctype not in ("Thai PND 3 Filing", "Thai PND 53 Filing"):
		frappe.throw(_("Unsupported PND filing type."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Submit the filing before exporting for RDPrep."))

	content = build_rdprep_text(doc)
	frappe.response.filename = f"{doc.pnd_type.replace(' ', '')}-{getdate(doc.tax_period):%Y-%m}.txt"
	frappe.response.filecontent = content.encode("utf-8-sig")
	frappe.response.type = "download"
	frappe.response.display_content_as = "attachment"


def build_rdprep_text(doc: "PNDFiling") -> str:
	"""Validate filing snapshots and generate one first-slot income row per item."""
	if doc.pnd_type not in ("PND 3", "PND 53"):
		frappe.throw(_("Unsupported PND filing type."))
	if not doc.items or len(doc.items) > 99999:
		frappe.throw(_("RDPrep requires between 1 and 99999 export rows."))
	validate_rdprep_tax_id(doc.company_tax_id, _("Company Tax ID"))
	period = getdate(doc.tax_period)
	columns = (
		"seq",
		"id13",
		"branchNo",
		"titleName",
		"firstName",
		"middleName",
		"surname",
		"subdistrict",
		"district",
		"province",
		"postCode",
		"date1",
		"incomeTaxDesc1",
		"taxRate1",
		"incomeAmt1",
		"netAmt1",
		"condition1",
		"addressLine1Reference",
		"addressLine2Reference",
	)
	lines = ["|".join(columns)]
	for index, item in enumerate(doc.items, 1):
		lines.append("|".join(build_rdprep_row(doc, item, index, period)))
	return "\r\n".join(lines) + "\r\n"


def build_rdprep_row(doc, item, index, period):
	"""Validate one recipient snapshot and keep free-form addresses unmapped."""
	label = _("Row {0}").format(index)
	validate_rdprep_tax_id(item.recipient_tax_id, label)
	if item.recipient_tax_id == doc.company_tax_id:
		frappe.throw(_("{0}: Recipient Tax ID must differ from Company Tax ID.").format(label))
	prefix = item.recipient_tax_id[:3]
	if doc.pnd_type == "PND 53":
		if not ("010" <= prefix <= "096" or item.recipient_tax_id.startswith(("0993", "0994"))):
			frappe.throw(_("{0}: Recipient Tax ID is not valid for PND53.").format(label))
	elif prefix == "099" and not item.recipient_tax_id.startswith(("0991", "0992")):
		frappe.throw(_("{0}: Recipient Tax ID is not valid for PND3.").format(label))
	branch = item.recipient_branch_code or ""
	if not re.fullmatch(r"[0-9]{5}", branch):
		frappe.throw(_("{0}: Branch Code must contain five digits.").format(label))
	date = getdate(item.payment_date) if item.payment_date else None
	if not date or (date.year, date.month) != (period.year, period.month) or date > getdate(nowdate()):
		frappe.throw(
			_("{0}: Payment date must match the filing period and cannot be in the future.").format(label)
		)
	income = rdprep_decimal(item.base_amount, label)
	tax = rdprep_decimal(item.tax_amount, label)
	rate = rdprep_decimal(item.tax_rate, label)
	if not 0 < rate <= 35:
		frappe.throw(
			_("{0}: RDPrep tax rate must be greater than zero and at most 35 percent.").format(label)
		)
	if (
		income < 0
		or tax < 0
		or income == tax == 0
		or (doc.filing_type == "Normal" and (income <= 0 or tax > income))
	):
		frappe.throw(_("{0}: Income or tax amount is not valid for this filing type.").format(label))
	if abs(tax - income * rate / 100) > Decimal("0.99"):
		frappe.throw(_("{0}: Tax differs from income times rate by more than 0.99.").format(label))
	condition = rdprep_condition(doc.pnd_type, item.tax_payment_condition, label)
	is_pnd3 = doc.pnd_type == "PND 3"
	values = [
		str(index),
		item.recipient_tax_id,
		branch,
		rdprep_text(item.get("recipient_title"), label, "titleName", 100, required=is_pnd3),
		rdprep_text(
			item.recipient_first_name if is_pnd3 else item.recipient_name,
			label,
			"firstName",
			160 if is_pnd3 else 320,
			required=True,
		),
		"",
		rdprep_text(item.recipient_last_name, label, "surname", 160) if is_pnd3 else "",
		rdprep_text(item.subdistrict, label, "subdistrict", 100),
		rdprep_text(item.district, label, "district", 100),
		rdprep_text(item.province, label, "province", 100),
		rdprep_text(item.postal_code, label, "postCode", 5),
		date.isoformat(),
		rdprep_text(item.income_description, label, "incomeTaxDesc1", 200, required=True),
		f"{rate:f}",
		f"{income:.2f}",
		f"{tax:.2f}",
		condition,
		rdprep_text(item.address_line1, label, "addressLine1Reference", 0, reference=True),
		rdprep_text(item.address_line2, label, "addressLine2Reference", 0, reference=True),
	]
	if values[10] and not re.fullmatch(r"[0-9]{5}", values[10]):
		frappe.throw(_("{0}: Postcode must contain five digits.").format(label))
	return values


def rdprep_text(
	value: str | None, label: str, field: str, limit: int, *, required: bool = False, reference: bool = False
) -> str:
	"""Reject unsafe values instead of silently changing names or addresses."""
	value = (value or "").strip()
	if required and not value:
		frappe.throw(_("{0}: {1} is required for RDPrep.").format(label, field))
	if limit and len(value) > limit:
		frappe.throw(_("{0}: {1} exceeds {2} characters.").format(label, field, limit))
	if re.search(r"[|\r\n\x00-\x1f]", value) or (
		not reference and re.search(r"[^\u0E00-\u0E7F0-9a-zA-Z,.`~!@#$%&*()\-_=+\\;:/ \t]", value)
	):
		frappe.throw(_("{0}: {1} contains characters that RDPrep cannot import.").format(label, field))
	return value


def rdprep_decimal(value: object, label: str) -> Decimal:
	"""Reject non-finite numbers and precision that RDPrep would reject."""
	try:
		number = Decimal(str(value))
	except InvalidOperation:
		frappe.throw(_("{0}: Invalid RDPrep number.").format(label))
	if not number.is_finite() or abs(number) >= Decimal("1e15") or number != number.quantize(Decimal("0.01")):
		frappe.throw(
			_("{0}: RDPrep amounts require at most 15 integer digits and two decimal places.").format(label)
		)
	return number


def rdprep_condition(pnd_type: str, value: str, label: str) -> str:
	"""Use bundled import codes, not RDPrep internal form keys."""
	codes = {
		"PND 3": {"Withheld": "0", "Payer Bears Tax Continuously": "1", "Payer Bears Tax One Time": "2"},
		"PND 53": {"Withheld": "1", "Payer Bears Tax Continuously": "2", "Payer Bears Tax One Time": "2"},
	}
	if value not in codes[pnd_type]:
		frappe.throw(_("{0}: Unsupported tax payment condition.").format(label))
	return codes[pnd_type][value]


def validate_rdprep_tax_id(value: str, label: str) -> None:
	"""Match the importer checksum and its explicit dummy-ID block list."""
	dummy_ids = {
		"1111111111119",
		"2222222222227",
		"0000000000001",
		"1212121212121",
		"3333333333335",
		"4444444444443",
		"5555555555551",
		"6666666666660",
		"7777777777778",
		"8888888888886",
		"9999999999994",
		"0111111111111",
		"1234567891011",
	}
	if not re.fullmatch(r"[0-9]{13}", value or "") or value in dummy_ids:
		frappe.throw(_("{0}: Invalid RDPrep Tax ID.").format(label))
	checksum = (11 - sum(int(digit) * (13 - index) for index, digit in enumerate(value[:12])) % 11) % 10
	if checksum != int(value[-1]):
		frappe.throw(_("{0}: Invalid RDPrep Tax ID checksum.").format(label))
