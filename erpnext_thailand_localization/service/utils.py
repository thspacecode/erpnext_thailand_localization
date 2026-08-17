import re

import frappe
from frappe import _


def normalize_digits(value: str | None) -> str:
	return re.sub(r"\D", "", value or "")


def normalize_branch_code(value: str | None) -> str:
	digits = normalize_digits(value)
	return digits.zfill(5) if digits else "00000"


def validate_tax_id(value: str | None, label: str) -> None:
	if len(normalize_digits(value)) != 13:
		frappe.throw(_("{0} must contain exactly 13 digits.").format(label))


def validate_branch_code(value: str | None, label: str) -> None:
	if len(normalize_digits(value)) != 5:
		frappe.throw(_("{0} must contain exactly 5 digits.").format(label))
