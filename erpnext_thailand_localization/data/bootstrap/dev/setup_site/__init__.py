from pathlib import Path

import frappe
from frappe import _

from erpnext_thailand_localization.data.bootstrap.abc.setup_site import SetupSite


class SetupSiteDev(SetupSite):
	data_csv_path = Path(__file__).parent / "assets"

	def hotfix_standard_price(self) -> None:
		"""Pre-seed ERPNext defaults required before its setup wizard runs."""
		self.csv_loader("Price List", insert_only=True)

	def complete_setup_wizard(self) -> None:
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

		if not frappe.is_setup_complete():
			frappe.throw(
				_("Setup wizard did not complete. Reset the disposable site before retrying bootstrap.")
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
