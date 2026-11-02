import frappe
from frappe import _

from erpnext_thailand_localization.data.abc import Report
from erpnext_thailand_localization.data.abc.helper.dev_bootstrap_marker import (
	bootstrap_dev_is_done,
	mark_bootstrap_dev_as_done,
)
from erpnext_thailand_localization.data.bootstrap.dev.setup_accounting import SetupAccountingDev
from erpnext_thailand_localization.data.bootstrap.dev.setup_master_data import SetupMasterDataDev
from erpnext_thailand_localization.data.bootstrap.dev.setup_site import SetupSiteDev
from erpnext_thailand_localization.data.bootstrap.dev.setup_transactions import SetupTransactionsDev


def execute() -> Report:
	"""Initialize a fresh disposable site once. The caller owns the final commit.

	Adapted from the bootstrap skill demo. Reject an already configured site
	without a marker instead of adopting or changing its existing records.
	Reset the disposable site after any partial failure.
	"""
	report: Report = {"created": {}, "updated": {}, "skipped": {}}
	if bootstrap_dev_is_done():
		return report
	if frappe.is_setup_complete():
		frappe.throw(
			_(
				"Development bootstrap requires a fresh disposable site. Do not run it on production. Reset the disposable site after a partial failure."
			)
		)
	for step in (SetupSiteDev, SetupAccountingDev, SetupMasterDataDev, SetupTransactionsDev):
		result = step().make()
		for change_type, doctypes in result.items():
			for doctype, names in doctypes.items():
				report[change_type].setdefault(doctype, []).extend(names)
	mark_bootstrap_dev_as_done()
	return report
