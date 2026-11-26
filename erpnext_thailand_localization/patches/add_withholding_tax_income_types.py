from erpnext_thailand_localization.data.initial_data import SetupInitialData


def execute():
	SetupInitialData().csv_loader("Thai Withholding Tax Income Type", skip_existing=True)
