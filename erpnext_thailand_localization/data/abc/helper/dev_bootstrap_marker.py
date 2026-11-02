import frappe
from frappe.utils import cint


def bootstrap_dev_is_done() -> bool:
	return bool(
		cint(
			frappe.defaults.get_defaults_for("__default").get(
				"erpnext_thailand_localization_dev_bootstrap_completed"
			)
		)
	)


def mark_bootstrap_dev_as_done() -> None:
	frappe.defaults.set_global_default("erpnext_thailand_localization_dev_bootstrap_completed", True)
