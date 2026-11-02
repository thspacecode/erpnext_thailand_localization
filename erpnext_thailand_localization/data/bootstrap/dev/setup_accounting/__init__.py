from pathlib import Path

import frappe

from erpnext_thailand_localization.data.bootstrap.abc.setup_accounting import SetupAccounting


class SetupAccountingDev(SetupAccounting):
	data_csv_path = Path(__file__).parent / "assets"

	def make_account(self) -> None:
		self.csv_loader(
			"Account",
			insert_only=True,
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
				"enable_sales_withholding_tax": 1,
				"sales_withholding_tax_account": (f"Sales Withholding Tax Receivable - {self.company_abbr}"),
				"enable_purchase_withholding_tax": 1,
				"purchase_withholding_tax_pnd3_account": (
					f"Purchase Withholding Tax PND 3 Payable - {self.company_abbr}"
				),
				"purchase_withholding_tax_pnd53_account": (
					f"Purchase Withholding Tax PND 53 Payable - {self.company_abbr}"
				),
			}
		)
		company.save()
