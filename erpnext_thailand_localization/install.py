from erpnext_thailand_localization.initial_data import SetupInitialData


def after_install():
	return SetupInitialData().make()
