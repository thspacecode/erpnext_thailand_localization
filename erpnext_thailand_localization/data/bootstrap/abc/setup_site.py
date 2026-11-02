from abc import abstractmethod

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.bootstrap.abc.bootstrap_step import BootstrapStep


class SetupSite(BootstrapStep):
	def make(self) -> Report:
		self.hotfix_standard_price()
		self.complete_setup_wizard()
		self.complete_module_onboarding()
		return self.report

	@abstractmethod
	def hotfix_standard_price(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def complete_setup_wizard(self) -> None:
		raise NotImplementedError

	@abstractmethod
	def complete_module_onboarding(self) -> None:
		raise NotImplementedError
