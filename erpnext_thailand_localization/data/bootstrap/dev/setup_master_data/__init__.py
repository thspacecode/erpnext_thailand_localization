from pathlib import Path

import frappe

from erpnext_thailand_localization.data.bootstrap.abc.setup_master_data import SetupMasterData


class SetupMasterDataDev(SetupMasterData):
	data_csv_path = Path(__file__).parent / "assets"

	def make_customer(self) -> None:
		self.csv_loader("Customer", insert_only=True)

	def make_supplier(self) -> None:
		self.csv_loader("Supplier", insert_only=True)

	def set_thai_localization_settings(self) -> None:
		settings = frappe.get_doc("Thai Localization Settings")
		settings.revenue_department = "Revenue Department"
		settings.save()

	def make_item(self) -> None:
		self.csv_loader("Item", insert_only=True)

	def make_party_addresses(self) -> None:
		self.csv_loader("Address", insert_only=True)
