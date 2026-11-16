import frappe
from frappe.www.printview import get_context as get_standard_context

no_cache = 1


def get_context(context):
	context.update(get_standard_context(context))
	context.pp30_print = frappe.form_dict.get("format") in (
		"PP30 Summary",
		"PP30 Purchase VAT Report",
		"PP30 Sales VAT Report",
	)

	return context
