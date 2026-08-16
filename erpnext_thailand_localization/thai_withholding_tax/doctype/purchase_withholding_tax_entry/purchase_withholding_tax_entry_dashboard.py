import frappe
from frappe import _


def get_data() -> frappe._dict:
	"""Show PND filings linked through their filing item rows."""
	return frappe._dict(
		{
			"fieldname": "purchase_withholding_tax_entry",
			"transactions": [
				{
					"label": _("PND Filing"),
					"items": ["Thai PND 3 Filing", "Thai PND 53 Filing"],
				}
			],
		}
	)
