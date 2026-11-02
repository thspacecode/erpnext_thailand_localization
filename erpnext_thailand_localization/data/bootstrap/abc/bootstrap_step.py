import frappe
from frappe.utils import now_datetime

from erpnext_thailand_localization.data.abc import BaseImporter


class BootstrapStep(BaseImporter):
	def __init__(self) -> None:
		super().__init__()
		self.now = now_datetime()
		self.company = "Dunder Mifflin"
		self.company_abbr = "DM"

	def get_leaf_account(self, root_type: str, account_type: str | None = None) -> str:
		filters = {
			"company": self.company,
			"root_type": root_type,
			"is_group": 0,
			"disabled": 0,
		}
		if account_type:
			filters["account_type"] = account_type

		account = frappe.db.get_value("Account", filters, "name", order_by="lft asc")
		if not account and account_type:
			filters.pop("account_type")
			account = frappe.db.get_value("Account", filters, "name", order_by="lft asc")
		if not account:
			frappe.throw(f"No active {root_type} account exists for Company {self.company}.")
		return account

	def get_company_account(self, default_field: str, root_type: str, account_type: str) -> str:
		account = frappe.get_cached_value("Company", self.company, default_field)
		if account and not frappe.get_cached_value("Account", account, "is_group"):
			return account
		return self.get_leaf_account(root_type, account_type)
