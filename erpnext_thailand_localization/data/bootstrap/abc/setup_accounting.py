from abc import abstractmethod

import frappe

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.bootstrap.abc.bootstrap_step import BootstrapStep


class SetupAccounting(BootstrapStep):
	def make(self) -> Report:
		self.make_account()
		self.update_company()
		return self.report

	@abstractmethod
	def make_account(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def update_company(self) -> None:
		raise NotImplementedError

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
