from erpnext_thailand_localization.data.initial_data import SetupInitialData


def after_install():
	return SetupInitialData().make()
