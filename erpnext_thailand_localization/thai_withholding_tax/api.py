import frappe
from frappe.utils import flt


@frappe.whitelist()
def fetch_wht_detail(item_code: str) -> dict:
	item = frappe.get_doc("Item", item_code)
	item.check_permission("read")

	if item.custom_thai_withholding_tax_income_type:
		return {
			"income_type": item.custom_thai_withholding_tax_income_type,
			"tax_rate": flt(item.custom_thai_withholding_tax_rate),
			"source": "Item",
		}

	group_values = frappe.db.get_value(
		"Item Group",
		item.item_group,
		["custom_thai_withholding_tax_income_type", "custom_thai_withholding_tax_rate"],
		as_dict=True,
	)
	if group_values and group_values.custom_thai_withholding_tax_income_type:
		return {
			"income_type": group_values.custom_thai_withholding_tax_income_type,
			"tax_rate": flt(group_values.custom_thai_withholding_tax_rate),
			"source": "Item Group",
		}

	return {"income_type": None, "tax_rate": 0, "source": None}
