from typing import Any, ClassVar

import frappe
from frappe.model.document import Document

from erpnext_thailand_localization.types import Json


class DocTypeFactory[T: Document]:
	"""Build and insert test documents with overridable defaults."""

	doctype: ClassVar[str | None] = None

	@classmethod
	def defaults(cls) -> Json[T]:
		return {}

	@classmethod
	def build(cls, **overrides: Any) -> T:
		if not cls.doctype:
			raise TypeError(f"{cls.__name__} must define 'doctype'")

		return frappe.get_doc(
			{
				"doctype": cls.doctype,
				**cls.defaults(),
				**overrides,
			}
		)

	@classmethod
	def create(
		cls,
		*,
		ignore_permissions: bool = False,
		submit: bool = False,
		**overrides: Any,
	) -> T:
		doc = cls.build(**overrides)
		doc.insert(ignore_permissions=ignore_permissions)
		if submit:
			doc.submit()
		return doc
