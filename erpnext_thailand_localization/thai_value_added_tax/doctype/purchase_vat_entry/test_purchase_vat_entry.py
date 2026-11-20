import unittest
from unittest.mock import patch

import frappe

from erpnext_thailand_localization.controllers.t_vat_entry import VATEntryTest


class TestPurchaseVATEntry(VATEntryTest.TestCase):
	entry_doctype = "Purchase VAT Entry"


class TestPurchaseVATLedger(unittest.TestCase):
	def test_on_submit(self):
		"""Ordinary VAT register records must not post a second input VAT ledger."""
		# Arrange: No undue account means the source already recognized input VAT.
		entry = frappe.get_doc(doctype="Purchase VAT Entry", tax_base=1000, tax_amount=70)
		with patch(
			"erpnext_thailand_localization.thai_value_added_tax.doctype.purchase_vat_entry.purchase_vat_entry.make_gl_entries"
		) as post:
			# Act and assert: Register-only submission does not call the GL service.
			entry.on_submit()
			post.assert_not_called()
