from functools import lru_cache
from typing import Any

import frappe
from frappe.handler import is_valid_http_method
from frappe.tests.utils import whitelist_for_tests

from erpnext_thailand_localization.data.test_data.bootstrap_test_master_data import BootStrapTestMasterData
from erpnext_thailand_localization.tests.factories.base import DocTypeFactory
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite

# Importing test utilities bootstraps the shared records, following erpnext.tests.utils.
boot_strap_test_master_data = BootStrapTestMasterData()
boot_strap_test_master_data.make()


@lru_cache
def get_factory(doctype: str) -> type[DocTypeFactory]:
	"""Return the factory class declared for a DocType."""
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(f"DocType {doctype} does not exist", frappe.DoesNotExistError)

	module_name = f"erpnext_thailand_localization.tests.factories.{frappe.scrub(doctype)}"
	try:
		factory_module = frappe.get_module(module_name)
	except ModuleNotFoundError as error:
		if error.name != module_name:
			raise
		frappe.throw(f"Factory module not found for DocType {doctype}", frappe.DoesNotExistError)

	factory_classes = {
		candidate
		for candidate in vars(factory_module).values()
		if isinstance(candidate, type)
		and issubclass(candidate, DocTypeFactory)
		and candidate is not DocTypeFactory
		and candidate.doctype == doctype
	}
	if len(factory_classes) != 1:
		frappe.throw(f"Expected one factory for DocType {doctype}, found {len(factory_classes)}")

	return factory_classes.pop()


@whitelist_for_tests()
def run_factory_method(
	doctype: str,
	method: str,
	args: str | dict[str, Any] | None = None,
) -> object:
	"""Resolve a factory and execute one of its whitelisted methods."""
	factory_class = get_factory(doctype)
	method_object = getattr(factory_class, method, None)
	if not callable(method_object):
		frappe.throw(f"Factory for {doctype} has no method {method}", frappe.DoesNotExistError)

	function = getattr(method_object, "__func__", method_object)
	frappe.is_whitelisted(function)
	if getattr(frappe.local, "request", None):
		is_valid_http_method(function)

	method_args = frappe.parse_json(args) if isinstance(args, str) else args or {}
	if not isinstance(method_args, dict):
		frappe.throw("Factory method arguments must be a JSON object")

	return frappe.call(method_object, **method_args)
