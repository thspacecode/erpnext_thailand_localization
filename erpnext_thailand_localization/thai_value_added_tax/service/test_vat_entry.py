from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from erpnext_thailand_localization.thai_value_added_tax.service.vat_entry import (
	cancel_entries,
	create_entries,
	generation_key,
	group_rows,
)


class TestVATEntryService(TestCase):
	def row(self, identity="a", **values):
		"""Build explicit source data without linked master setup."""
		return dict(
			source_identity=identity,
			direction="Sales",
			party="Customer",
			tax_invoice_number="INV-1",
			vat_category="Taxable",
			rate=7,
			tax_base=100,
			tax_amount=7,
			**values,
		)

	def test_group_rows(self):
		"""Group only compatible invoices; preserve signed actual VAT and distinct categories."""
		rows = [self.row(), self.row("b")]
		rows.append(dict(self.row("c"), vat_category="Zero Rated", tax_amount=0, rate=0))
		rows.append(dict(self.row("d"), vat_category="Exempt", tax_amount=0, rate=0))
		rows.append(dict(self.row("e"), tax_invoice_number="SPLIT", tax_base=-100, tax_amount=-6.99))
		groups = group_rows(rows)
		self.assertEqual(len(groups), 4)
		self.assertEqual(groups[0].tax_base, 200)
		self.assertEqual(groups[0].tax_amount, 14)
		self.assertEqual(str(groups[-1].tax_amount), "-6.99")
		with self.assertRaisesRegex(frappe.ValidationError, "identity"):
			group_rows([self.row(), self.row()])
		with self.assertRaisesRegex(frappe.ValidationError, "explicit VAT category"):
			group_rows([dict(self.row(), vat_category=None, tax_amount=0)])

	def test_generation_key(self):
		"""Keep retry keys stable and separate amendments and document types."""
		self.assertEqual(
			generation_key("Sales Invoice", "A", "row"), generation_key("Sales Invoice", "A", "row")
		)
		self.assertNotEqual(
			generation_key("Sales Invoice", "A", "row"), generation_key("Sales Invoice", "A-1", "row")
		)
		self.assertNotEqual(
			generation_key("Sales Invoice", "A", "row"), generation_key("Purchase Invoice", "A", "row")
		)

	def test_create_entries(self):
		"""Retries return the reviewed entry without writing defaults over it."""
		source = MagicMock(doctype="Sales Invoice", company="Company", docstatus=1)
		source.name = "INV-1"
		source.get.return_value = "Customer"
		reviewed = MagicMock(tax_invoice_number="CHECKED")
		with (
			patch("frappe.get_cached_doc", return_value=frappe._dict(default_currency="THB")),
			patch("frappe.db.get_value", return_value="VAT-1"),
			patch("frappe.get_doc", return_value=reviewed),
			patch("frappe.new_doc") as new_doc,
		):
			self.assertEqual(create_entries(source, [self.row()]), [reviewed])
			new_doc.assert_not_called()
			self.assertEqual(reviewed.tax_invoice_number, "CHECKED")

	def test_cancel_entries(self):
		"""A PP30 failure must stop all changes, including draft tombstones."""
		first, second = MagicMock(docstatus=0), MagicMock(docstatus=1)
		second.before_cancel.side_effect = frappe.ValidationError("Cancel the submitted PP30")
		with patch(
			"erpnext_thailand_localization.thai_value_added_tax.service.vat_entry.find_entries",
			return_value=[first, second],
		):
			with self.assertRaisesRegex(frappe.ValidationError, "submitted PP30"):
				cancel_entries(MagicMock())
			first.db_set.assert_not_called()
			second.cancel.assert_not_called()
			second.before_cancel.side_effect = None
			cancel_entries(MagicMock())
			first.db_set.assert_called_once_with("docstatus", 2, update_modified=True)
			second.cancel.assert_called_once()
