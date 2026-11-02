"""Compatibility entry points. All bootstrap commands now initialize once."""

from erpnext_thailand_localization.data.bootstrap.dev.bootstrap import execute


def bootstrap_test_master_data():
	return execute()


def bootstrap_all_data():
	return execute()


def bootstrap_dev_data():
	return execute()
