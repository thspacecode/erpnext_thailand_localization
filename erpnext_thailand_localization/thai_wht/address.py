from typing import TYPE_CHECKING

from frappe import _

from erpnext_thailand_localization.service.utils import (
	normalize_branch_code,
	validate_branch_code,
)

if TYPE_CHECKING:
	from frappe.contacts.doctype.address.address import Address


def validate_address(address: "Address", method: str | None = None) -> None:
	branch_code = normalize_branch_code(address.get("branch_code"))
	address.set("branch_code", branch_code)
	validate_branch_code(branch_code, _("Branch Code"))
