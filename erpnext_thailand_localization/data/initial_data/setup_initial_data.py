from pathlib import Path

from erpnext_thailand_localization.data.abc import BaseImporter, Report


class SetupInitialData(BaseImporter):
	"""Set up initial data for ERPNext Thailand Localization DocTypes.

	Fixtures are intentionally not used because this data must remain dynamic and be
	maintained by the company's accounting team.
	"""

	data_csv_path = Path(__file__).parent / "data_csv"

	def make(self) -> Report:
		self.csv_loader("Thai Withholding Tax Category")
		self.csv_loader("Thai Withholding Tax Income Type")
		return self.report
