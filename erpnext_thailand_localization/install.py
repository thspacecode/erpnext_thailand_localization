from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.initial_data import SetupInitialData


def after_install() -> Report:
	return SetupInitialData().make()
