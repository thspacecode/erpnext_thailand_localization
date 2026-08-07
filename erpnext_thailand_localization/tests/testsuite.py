import uuid
from contextlib import contextmanager

import frappe
from frappe.model.document import Document
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import load_test_records_for


class ERPNextThaiTestSuite(IntegrationTestCase):
	"""
	Copied from ERPNextThaiTestSuite, we can't import from erpnext.tests.utils
	because it'll init ERPNext's BootStrapTestData class which we don't want.

	This class should inherit from Frappe's IntegrationTestCase if not
	`before_tests` hooks won't get run.
	(before_tests hooks only fire for "integration" and "old-frappe-test-class-category" categories (see runner.py:100-108).)
	"""

	@classmethod
	def registerAs(cls, _as):
		def decorator(cm_func):
			setattr(cls, cm_func.__name__, _as(cm_func))
			return cm_func

		return decorator

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.globalTestRecords = {}

	def tearDown(self):
		frappe.db.rollback()

	def load_test_records(self, doctype):
		if doctype not in self.globalTestRecords:
			records = load_test_records_for(doctype)
			self.globalTestRecords[doctype] = records[doctype]

	@staticmethod
	def insert_doc(doc_dict) -> Document:
		doc = frappe.new_doc(doctype=doc_dict.get("doctype"))
		doc.update(doc_dict)
		doc.save()
		return doc

	@contextmanager
	def set_user(self, user: str):
		try:
			old_user = frappe.session.user
			frappe.set_user(user)
			yield
		finally:
			frappe.set_user(old_user)

	@contextmanager
	def set_flags(self, **flags):
		"""Temporarily set `frappe.flags`, restoring the previous values on exit."""
		previous = {name: frappe.flags.get(name) for name in flags}
		try:
			frappe.flags.update(flags)
			yield
		finally:
			frappe.flags.update(previous)

	@contextmanager
	def set_create_user(self, roles: list[str] | None = None):
		"""Create an ephemeral User with the given roles and activate it as the
		session user for the duration of the block.

		The user only lives inside the surrounding test — `tearDown`'s
		`frappe.db.rollback()` reverts the insert, so each test starts from a
		clean role matrix without depending on fixture data in `User.csv`.
		"""
		email = f"test_user_{uuid.uuid4().hex[:12]}@summit.com"
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Test"
		user.send_welcome_email = 0
		for role in roles or []:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)

		with self.set_user(email):
			yield email


@ERPNextThaiTestSuite.registerAs(staticmethod)
@contextmanager
def change_settings(doctype, settings_dict=None, /, **settings) -> None:
	"""Temporarily: change settings in a settings doctype."""
	import copy

	if settings_dict is None:
		settings_dict = settings

	settings = frappe.get_doc(doctype)
	previous_settings = copy.deepcopy(settings_dict)
	for key in previous_settings:
		previous_settings[key] = getattr(settings, key)

	for key, value in settings_dict.items():
		setattr(settings, key, value)
	settings.save(ignore_permissions=True)

	yield

	settings = frappe.get_doc(doctype)
	for key, value in previous_settings.items():
		setattr(settings, key, value)
	settings.save(ignore_permissions=True)
