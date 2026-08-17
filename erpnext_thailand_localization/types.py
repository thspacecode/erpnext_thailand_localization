from typing import Any

from frappe.model.document import Document

type Json[T: Document] = dict[str, Any]
