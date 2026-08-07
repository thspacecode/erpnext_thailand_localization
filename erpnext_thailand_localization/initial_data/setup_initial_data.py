from pathlib import Path

from erpnext_thailand_localization.data.abc import BaseImporter, Report


class SetupInitialData(BaseImporter):
	data_csv_path = Path(__file__).parent / "data_csv"

	def make(self) -> Report:
		self.csv_loader("Thai Withholding Tax Category")
		self.csv_loader("Thai Withholding Tax Income Type")
		return self.report
