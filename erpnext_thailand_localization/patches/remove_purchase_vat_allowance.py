import frappe


def execute():
	for doctype in ("Item", "Item Group"):
		name = f"{doctype}-custom_allow_undue_purchase_value_added_tax"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name)
