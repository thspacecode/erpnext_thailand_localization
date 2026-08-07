import frappe

from erpnext_thailand_localization.data.abc import BaseImporter, Report
from erpnext_thailand_localization.thai_withholding_tax.income_types import INCOME_TYPES


class SetupInitialData(BaseImporter):
	def setup_income_types(self):
		doctype = "Thai Withholding Tax Income Type"

		for values in INCOME_TYPES:
			name = values["income_type_name"]
			expected_values = {**values, "disabled": 0}

			if not frappe.db.exists(doctype, name):
				frappe.get_doc({"doctype": doctype, **expected_values}).insert()
				self.record_change("created", doctype, name)
				continue

			doc = frappe.get_doc(doctype, name)
			changed_values = {
				fieldname: value
				for fieldname, value in expected_values.items()
				if doc.get(fieldname) != value
			}
			if changed_values:
				doc.update(changed_values)
				doc.save()
				self.record_change("updated", doctype, name)
			else:
				self.record_change("skipped", doctype, name)

	def make(self) -> Report:
		self.setup_income_types()
		return self.report
