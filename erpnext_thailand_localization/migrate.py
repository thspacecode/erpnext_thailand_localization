import frappe

from erpnext_thailand_localization.data.bootstrap.dev.bootstrap import execute


def before_tests() -> None:
	execute()
	frappe.db.commit()
