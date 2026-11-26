import frappe
from frappe import _


def get_dashboard_data(data: frappe._dict) -> frappe._dict:
	"""Add withholding tax entries linked through their item rows."""
	data.setdefault("non_standard_fieldnames", {}).update(
		{
			"Sales WHT Entry": "reference_doc",
			"Purchase WHT Entry": "reference_doc",
		}
	)
	data.setdefault("dynamic_links", {})["reference_doc"] = [
		"Payment Entry",
		"reference_doc_doctype",
	]

	data.setdefault("transactions", []).append(
		{
			"label": _("Withholding Tax"),
			"items": [
				"Sales WHT Entry",
				"Purchase WHT Entry",
			],
		}
	)

	return data
