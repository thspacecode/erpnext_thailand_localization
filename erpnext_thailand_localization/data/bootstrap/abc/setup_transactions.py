from abc import abstractmethod

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.bootstrap.abc.bootstrap_step import BootstrapStep


class SetupTransactions(BootstrapStep):
	@abstractmethod
	def make(self) -> Report:
		raise NotImplementedError
