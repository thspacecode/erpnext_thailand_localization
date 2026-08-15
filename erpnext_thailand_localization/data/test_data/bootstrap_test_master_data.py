from pathlib import Path

import frappe
from frappe.utils import now_datetime

from erpnext_thailand_localization.data.abc import BaseImporter, Report


class BootStrapTestMasterData(BaseImporter):
	"""Set up reusable ERPNext prerequisites for development and tests."""

	data_csv_path = Path(__file__).parent / "data_csv"

	def define_share_val(self) -> None:
		self.now = now_datetime()

		# This mock company sells paper products.
		# The boss is the world's best boss, Michael Scott.
		# When creating mock data, ensure it is relevant to the company's business.
		self.company = "Dunder Mifflin"
		self.company_abbr = "DM"

	def make(self) -> Report:
		self.define_share_val()

		self.hotfix_standard_price()

		self.complete_setup_wizard()
		self.complete_module_onboarding()

		self.make_account()

		self.update_company()

		self.make_customer()
		self.make_supplier()
		self.make_item()
		self.make_party_addresses()

		frappe.db.commit()  # nosemgrep

		return self.report

	# ---
	# Maker Method
	# ---

	def hotfix_standard_price(self) -> None:
		"""Pre-seed ERPNext defaults required before its setup wizard runs."""
		self.csv_loader("Price List")

	def complete_setup_wizard(self) -> None:
		if frappe.is_setup_complete():
			return

		from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

		current_year = self.now.year
		setup_complete(
			{
				"currency": "THB",
				"country": "Thailand",
				"timezone": "Asia/Bangkok",
				"language": "English",
				"company_name": self.company,
				"company_abbr": self.company_abbr,
				"chart_of_accounts": "Standard",
				"fy_start_date": f"{current_year}-01-01",
				"fy_end_date": f"{current_year}-12-31",
				"setup_demo": 0,
			}
		)

	def complete_module_onboarding(self) -> None:
		for name in frappe.get_all(
			"Module Onboarding",
			filters={"is_complete": 0},
			pluck="name",
		):
			doc = frappe.get_doc("Module Onboarding", name)
			for step in doc.get_steps():
				step.db_set("is_complete", 1)
			doc.db_set("is_complete", 1)

	def make_account(self) -> None:
		self.csv_loader(
			"Account",
			csv_replacements={
				"company": self.company,
				"company_abbr": self.company_abbr,
				"asset_root": self.get_root_account("Asset"),
				"liability_root": self.get_root_account("Liability"),
			},
		)

	def update_company(self) -> None:
		company = frappe.get_doc("Company", self.company)
		company.update(
			{
				"tax_id": "0105555000001",
				"custom_thai_withholding_tax_category": "Juristic Person - Domestic",
				"sales_withholding_tax_account": (f"Sales Withholding Tax Receivable - {self.company_abbr}"),
				"purchase_withholding_tax_pnd3_account": (
					f"Purchase Withholding Tax PND 3 Payable - {self.company_abbr}"
				),
				"purchase_withholding_tax_pnd53_account": (
					f"Purchase Withholding Tax PND 53 Payable - {self.company_abbr}"
				),
			}
		)
		company.save()

	def make_customer(self) -> None:
		self.csv_loader("Customer")

	def make_supplier(self) -> None:
		self.csv_loader("Supplier")

	def make_item(self) -> None:
		self.csv_loader("Item")

	def make_party_addresses(self) -> None:
		self.csv_loader("Address")

	# ---
	# Helper Method
	# ---

	def get_root_account(self, root_type: str) -> str:
		root_accounts = [
			account
			for account in frappe.get_all(
				"Account",
				filters={"company": self.company, "root_type": root_type, "is_group": 1},
				fields=["name", "account_name", "parent_account"],
				order_by="lft asc",
			)
			if not account.parent_account
		]
		if not root_accounts:
			frappe.throw(f"No {root_type} root account exists for Company {self.company}.")

		matching_root = next(
			(account for account in root_accounts if account.account_name == root_type),
			root_accounts[0],
		)
		return matching_root.name

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
