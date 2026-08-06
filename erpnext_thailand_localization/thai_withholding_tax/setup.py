import frappe

from erpnext_thailand_localization.thai_withholding_tax.income_types import INCOME_TYPES


def seed_income_types():
	report = {"created": [], "skipped": []}
	for values in INCOME_TYPES:
		name = values["income_type_name"]
		if frappe.db.exists("Thai Withholding Tax Income Type", name):
			report["skipped"].append(name)
			continue

		frappe.get_doc(
			{
				"doctype": "Thai Withholding Tax Income Type",
				**values,
				"disabled": 0,
			}
		).insert()
		report["created"].append(name)

	return report
