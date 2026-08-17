from typing import TypedDict

from erpnext_thailand_localization.data.abc import Report


class BootstrapAllDataResult(TypedDict):
	master_data: Report
	dev_data: Report


class BootstrapDevDataResult(TypedDict):
	dev_data: Report
