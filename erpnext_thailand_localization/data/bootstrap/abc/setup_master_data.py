from abc import abstractmethod

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.bootstrap.abc.bootstrap_step import BootstrapStep


class SetupMasterData(BootstrapStep):
	def make(self) -> Report:
		self.make_customer()
		self.make_supplier()
		self.set_thai_localization_settings()
		self.make_item()
		self.make_party_addresses()
		return self.report

	@abstractmethod
	def make_customer(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def make_supplier(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def set_thai_localization_settings(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def make_item(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def make_party_addresses(self) -> None:
		raise NotImplementedError
