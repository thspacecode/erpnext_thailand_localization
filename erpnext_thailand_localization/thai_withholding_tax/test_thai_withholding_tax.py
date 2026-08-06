import importlib
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from erpnext_thailand_localization.thai_withholding_tax.api import fetch_wht_detail
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.income_types import INCOME_TYPES
from erpnext_thailand_localization.thai_withholding_tax.setup import seed_income_types


class TestThaiWithholdingTax(IntegrationTestCase):
	def test_modules_and_metadata(self):
		for module_name in ("Thai Withholding Tax", "Thai Value Added Tax"):
			module = frappe.get_doc("Module Def", module_name)
			self.assertEqual(module.app_name, "erpnext_thailand_localization")
			self.assertFalse(module.custom)
			importlib.import_module(f"erpnext_thailand_localization.{frappe.scrub(module_name)}")

		for doctype in (
			"Thai Withholding Tax Income Type",
			"Withholding Tax Entry Item",
			"Purchase Withholding Tax Entry",
			"Sales Withholding Tax Entry",
		):
			self.assertEqual(frappe.get_meta(doctype).module, "Thai Withholding Tax")

		self.assertTrue(frappe.get_meta("Purchase Withholding Tax Entry").is_submittable)
		self.assertTrue(frappe.get_meta("Sales Withholding Tax Entry").is_submittable)
		self.assertTrue(frappe.get_meta("Withholding Tax Entry Item").istable)

		income_permissions = {
			row.role: row for row in frappe.get_meta("Thai Withholding Tax Income Type").permissions
		}
		self.assertTrue(income_permissions["Accounts User"].read)
		self.assertFalse(income_permissions["Accounts User"].create)
		for doctype in ("Purchase Withholding Tax Entry", "Sales Withholding Tax Entry"):
			permissions = {row.role: row for row in frappe.get_meta(doctype).permissions}
			self.assertTrue(permissions["Accounts User"].submit)
			self.assertFalse(permissions["Accounts User"].delete)
			self.assertFalse(permissions["Accounts User"].cancel)
			self.assertTrue(permissions["Accounts Manager"].cancel)

	def test_custom_fields_and_hidden_generic_fields(self):
		for doctype in ("Item", "Item Group"):
			meta = frappe.get_meta(doctype, cached=False)
			self.assertEqual(
				meta.get_field("custom_thai_withholding_tax_income_type").options,
				"Thai Withholding Tax Income Type",
			)
			self.assertEqual(meta.get_field("custom_thai_withholding_tax_rate").fieldtype, "Percent")

		item_meta = frappe.get_meta("Item", cached=False)
		self.assertTrue(item_meta.get_field("purchase_tax_withholding_category").hidden)
		self.assertTrue(item_meta.get_field("sales_tax_withholding_category").hidden)

	def test_income_type_seed_is_complete_and_idempotent(self):
		report = seed_income_types()
		self.assertEqual(report["created"], [])
		self.assertEqual(len(report["skipped"]), 29)
		self.assertEqual(len(INCOME_TYPES), 29)
		self.assertEqual(frappe.db.count("Thai Withholding Tax Income Type"), 29)

		for expected in INCOME_TYPES:
			actual = frappe.db.get_value(
				"Thai Withholding Tax Income Type",
				expected["income_type_name"],
				["income_type_code", "description_th", "pnd1", "pnd2", "pnd3", "pnd53", "pnd54"],
				as_dict=True,
			)
			self.assertIsNotNone(actual)
			for fieldname, value in expected.items():
				if fieldname != "income_type_name":
					self.assertEqual(actual[fieldname], value)

	def test_server_calculation_overwrites_tax_and_updates_totals(self):
		doc = frappe.new_doc("Purchase Withholding Tax Entry")
		doc.company_currency = "THB"
		doc.append("items", {"base_amount": 1000, "tax_rate": 3, "tax_amount": 999})
		doc.append("items", {"base_amount": 250.55, "tax_rate": 0.5, "tax_amount": 999})

		doc.validate()

		self.assertEqual(doc.items[0].tax_amount, 30)
		self.assertEqual(doc.items[1].tax_amount, 1.25)
		self.assertEqual(doc.total_base_amount, 1250.55)
		self.assertEqual(doc.total_tax_amount, 31.25)

	@patch("erpnext_thailand_localization.thai_withholding_tax.api.frappe.db.get_value")
	@patch("erpnext_thailand_localization.thai_withholding_tax.api.frappe.get_doc")
	def test_fetch_wht_detail_keeps_defaults_at_one_level(self, get_doc, get_value):
		item = frappe._dict(
			custom_thai_withholding_tax_income_type="Item Income",
			custom_thai_withholding_tax_rate=0,
			item_group="Services",
			check_permission=MagicMock(),
		)
		get_doc.return_value = item

		self.assertEqual(
			fetch_wht_detail("ITEM-1"),
			{"income_type": "Item Income", "tax_rate": 0.0, "source": "Item"},
		)
		get_value.assert_not_called()
		item.check_permission.assert_called_once_with("read")

		item.custom_thai_withholding_tax_income_type = None
		get_value.return_value = frappe._dict(
			custom_thai_withholding_tax_income_type="Group Income",
			custom_thai_withholding_tax_rate=3.5,
		)
		self.assertEqual(
			fetch_wht_detail("ITEM-1"),
			{"income_type": "Group Income", "tax_rate": 3.5, "source": "Item Group"},
		)

		get_value.return_value = frappe._dict(
			custom_thai_withholding_tax_income_type=None,
			custom_thai_withholding_tax_rate=10,
		)
		self.assertEqual(fetch_wht_detail("ITEM-1"), {"income_type": None, "tax_rate": 0, "source": None})

	def test_purchase_and_sales_payment_entry_mappers(self):
		self.assert_mapper(
			make_purchase_withholding_tax_entry,
			payment_type="Pay",
			party_type="Supplier",
			party="Supplier A",
			target_doctype="Purchase Withholding Tax Entry",
			party_field="supplier",
			address_field="supplier_address",
		)
		self.assert_mapper(
			make_sales_withholding_tax_entry,
			payment_type="Receive",
			party_type="Customer",
			party="Customer A",
			target_doctype="Sales Withholding Tax Entry",
			party_field="customer",
			address_field="customer_address",
		)

	def assert_mapper(
		self,
		mapper,
		payment_type,
		party_type,
		party,
		target_doctype,
		party_field,
		address_field,
	):
		source = frappe._dict(
			name="PAY-0001",
			docstatus=1,
			payment_type=payment_type,
			party_type=party_type,
			party=party,
			company="Company A",
			posting_date="2026-01-15",
			check_permission=MagicMock(),
		)

		party_document = frappe._dict(check_permission=MagicMock())
		party_document[f"{frappe.scrub(party_type)}_primary_address"] = "Address A"
		company_document = frappe._dict(default_currency="THB", check_permission=MagicMock())
		address_document = frappe._dict(check_permission=MagicMock())

		def get_doc(doctype, name):
			return {
				"Payment Entry": source,
				party_type: party_document,
				"Company": company_document,
				"Address": address_document,
			}[doctype]

		target_template = frappe.new_doc(target_doctype)

		def map_doc(from_doctype, source_name, mapping, target_doc, postprocess):
			postprocess(source, target_template)
			return target_template

		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.get_doc",
				side_effect=get_doc,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.has_permission",
				return_value=True,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.get_mapped_doc",
				side_effect=map_doc,
			),
		):
			target = mapper(source.name)

		self.assertEqual(target.company, source.company)
		self.assertEqual(target.company_currency, "THB")
		self.assertEqual(target.payment_date, source.posting_date)
		self.assertEqual(target.get(party_field), party)
		self.assertEqual(target.get(address_field), "Address A")
		self.assertEqual(target.payment_entry, source.name)
		self.assertEqual(target.items, [])
		source.check_permission.assert_called_once_with("read")

	def test_mapper_rejects_unsubmitted_and_unsupported_payment_entries(self):
		for values in (
			{"docstatus": 0, "payment_type": "Pay", "party_type": "Supplier"},
			{"docstatus": 1, "payment_type": "Receive", "party_type": "Customer"},
		):
			source = frappe._dict(
				name="PAY-INVALID",
				party="Party A",
				company="Company A",
				posting_date="2026-01-15",
				check_permission=MagicMock(),
				**values,
			)
			with (
				patch(
					"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.get_doc",
					return_value=source,
				),
				self.assertRaises(frappe.ValidationError),
			):
				make_purchase_withholding_tax_entry(source.name)

	def test_mapper_enforces_source_read_and_target_create_permissions(self):
		source = frappe._dict(
			name="PAY-PERMISSION",
			docstatus=1,
			payment_type="Pay",
			party_type="Supplier",
			party="Supplier A",
			company="Company A",
			posting_date="2026-01-15",
			check_permission=MagicMock(side_effect=frappe.PermissionError),
		)
		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.get_doc",
				return_value=source,
			),
			self.assertRaises(frappe.PermissionError),
		):
			make_purchase_withholding_tax_entry(source.name)

		source.check_permission = MagicMock()
		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.get_doc",
				return_value=source,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.payment_entry.frappe.has_permission",
				return_value=False,
			),
			self.assertRaises(frappe.PermissionError),
		):
			make_purchase_withholding_tax_entry(source.name)

	def test_sales_certificate_rules(self):
		doc = frappe.new_doc("Sales Withholding Tax Entry")
		doc.docstatus = 1
		with self.assertRaisesRegex(frappe.ValidationError, "Certificate Number"):
			doc.validate_certificate()

		doc.certificate_number = "CERT-1"
		with self.assertRaisesRegex(frappe.ValidationError, "Certificate Attachment"):
			doc.validate_certificate()

		doc.certificate_attachment = "/private/files/cert.pdf"
		with (
			patch.object(frappe.db, "exists", return_value="SWHT-00001"),
			self.assertRaisesRegex(frappe.ValidationError, "already exists"),
		):
			doc.validate_certificate()

	def test_gl_and_reference_integrity(self):
		doc = frappe.new_doc("Purchase Withholding Tax Entry")
		doc.company = "Company A"
		doc.payment_entry = "PAY-0001"
		item = frappe._dict(gl_entry="GL-0001", idx=1)

		with patch.object(
			frappe.db,
			"get_value",
			return_value=frappe._dict(
				company="Company A",
				is_cancelled=0,
				voucher_type="Payment Entry",
				voucher_no="PAY-0001",
			),
		):
			doc.validate_gl_entry(item, "Row 1")

		item.update(
			{
				"reference_doc_doctype": "Purchase Invoice",
				"reference_doc": "PINV-1",
				"reference_doc_item_doctype": "Purchase Invoice Item",
				"reference_doc_item": "ROW-1",
			}
		)
		with (
			patch.object(
				frappe.db,
				"get_value",
				return_value=frappe._dict(parent="PINV-OTHER", parenttype="Purchase Invoice"),
			),
			self.assertRaisesRegex(frappe.ValidationError, "does not belong"),
		):
			doc.validate_reference(item, "Row 1")
