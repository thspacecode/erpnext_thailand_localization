import frappe
from frappe import _
from frappe.tests import UnitTestCase

from erpnext_thailand_localization.thai_withholding_tax.payment_entry_dashboard import (
	get_dashboard_data,
)


class TestPaymentEntryDashboard(UnitTestCase):
	def test_adds_withholding_tax_section_and_link_configuration(self) -> None:
		data = frappe._dict()

		result = get_dashboard_data(data)

		self.assertEqual(
			result.non_standard_fieldnames,
			{
				"Sales Withholding Tax Entry": "reference_doc",
				"Purchase Withholding Tax Entry": "reference_doc",
			},
		)
		self.assertEqual(
			result.dynamic_links,
			{"reference_doc": ["Payment Entry", "reference_doc_doctype"]},
		)
		self.assertEqual(
			result.transactions,
			[
				{
					"label": _("Withholding Tax"),
					"items": [
						"Sales Withholding Tax Entry",
						"Purchase Withholding Tax Entry",
					],
				}
			],
		)
