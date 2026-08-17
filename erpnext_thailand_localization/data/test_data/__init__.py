from erpnext_thailand_localization.data.abc import Report

from .bootstrap_dev_data import BootStrapDevData
from .bootstrap_test_master_data import BootStrapTestMasterData
from .types import BootstrapAllDataResult, BootstrapDevDataResult


def bootstrap_test_master_data() -> Report:
	return BootStrapTestMasterData().make()


def bootstrap_all_data() -> BootstrapAllDataResult:
	master_data = BootStrapTestMasterData().make()
	dev_data = BootStrapDevData().make()
	return {
		"master_data": master_data,
		"dev_data": dev_data,
	}


def bootstrap_dev_data() -> BootstrapDevDataResult:
	dev_data = BootStrapDevData().make()
	return {
		"dev_data": dev_data,
	}


__all__ = [
	"BootStrapDevData",
	"BootStrapTestMasterData",
	"BootstrapAllDataResult",
	"BootstrapDevDataResult",
]
