from abc import ABC, abstractmethod
from typing import Literal

ChangeType = Literal["created", "updated", "skipped"]
Report = dict[ChangeType, dict[str, list[str]]]


class BaseImporter(ABC):
	def __init__(self):
		self.report: Report = {
			"created": {},
			"updated": {},
			"skipped": {},
		}

	def record_change(self, change_type: ChangeType, doctype: str, name: str):
		self.report[change_type].setdefault(doctype, []).append(name)

	def merge_report(self, report: Report) -> Report:
		for change_type in ("created", "updated", "skipped"):
			for doctype, names in report[change_type].items():
				self.report[change_type].setdefault(doctype, []).extend(names)
		return self.report

	@abstractmethod
	def make(self) -> Report:
		return self.report
