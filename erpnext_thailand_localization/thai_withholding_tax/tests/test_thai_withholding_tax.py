import importlib
from unittest.mock import MagicMock, patch

import frappe

from erpnext_thailand_localization.data.initial_data import SetupInitialData
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite
from erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry import (
	make_purchase_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry import (
	make_sales_withholding_tax_entry,
)
from erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax import (
	apply_thai_withholding_tax,
	fetch_wht_detail,
)


class TestThaiWithholdingTax(ERPNextThaiTestSuite):
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

		for doctype, party_field in (
			("Purchase Withholding Tax Entry", "supplier"),
			("Sales Withholding Tax Entry", "customer"),
		):
			meta = frappe.get_meta(doctype, cached=False)
			field_order = [field.fieldname for field in meta.fields]
			self.assertEqual(
				field_order[field_order.index("company_section") : field_order.index("party_section")],
				["company_section", "company", "company_currency", "company_column", "payment_date"],
			)
			self.assertEqual(
				field_order[field_order.index("party_section") : field_order.index("items_section")],
				["party_section", party_field, "party_column", f"{party_field}_address"],
			)
			self.assertFalse(meta.has_field("payment_entry"))

		sales_meta = frappe.get_meta("Sales Withholding Tax Entry", cached=False)
		sales_field_order = [field.fieldname for field in sales_meta.fields]
		self.assertEqual(
			sales_field_order[
				sales_field_order.index("certificate_section") : sales_field_order.index("company_section")
			],
			[
				"certificate_section",
				"certificate_number",
				"certificate_column",
				"certificate_attachment",
			],
		)

		item_meta = frappe.get_meta("Withholding Tax Entry Item", cached=False)
		self.assertTrue(item_meta.istable)
		self.assertFalse(item_meta.has_field("gl_entry"))
		self.assertFalse(item_meta.has_field("accounting_evidence_section"))
		self.assertEqual(item_meta.get_field("reference_section").label, "Reference")

		income_type_meta = frappe.get_meta("Thai Withholding Tax Income Type", cached=False)
		self.assertEqual(
			[field.fieldname for field in income_type_meta.fields[:7]],
			[
				"income_type_name",
				"disabled",
				"income_type_section",
				"default_thai_withholding_tax_rate",
				"thai_withholding_tax_rate_by_category",
				"return_types_section",
				"thai_withholding_tax_category_pnd",
			],
		)
		self.assertFalse(income_type_meta.get_field("income_type_section").label)
		self.assertFalse(income_type_meta.get_field("return_types_section").label)
		self.assertFalse(income_type_meta.has_field("income_type_code"))
		rate_options = ["", "0", "0.5", "0.75", "1", "2", "3", "5", "10", "15"]
		default_rate = income_type_meta.get_field("default_thai_withholding_tax_rate")
		self.assertEqual(default_rate.fieldtype, "Select")
		self.assertEqual(default_rate.options.split("\n"), rate_options)
		self.assertFalse(income_type_meta.has_field("purchase_withholding_tax_account"))
		self.assertFalse(income_type_meta.has_field("sales_withholding_tax_account"))
		self.assertFalse(income_type_meta.has_field("thai_withholding_tax_rate"))
		self.assertFalse(income_type_meta.has_field("description_th"))

		income_permissions = {row.role: row for row in income_type_meta.permissions}
		self.assertTrue(income_permissions["Accounts User"].read)
		self.assertFalse(income_permissions["Accounts User"].create)
		for doctype in ("Purchase Withholding Tax Entry", "Sales Withholding Tax Entry"):
			permissions = {row.role: row for row in frappe.get_meta(doctype).permissions}
			self.assertTrue(permissions["Accounts User"].submit)
			self.assertFalse(permissions["Accounts User"].delete)
			self.assertFalse(permissions["Accounts User"].cancel)
			self.assertTrue(permissions["Accounts Manager"].cancel)

	def test_custom_fields_and_hidden_generic_fields(self):
		rate_options = ["", "0", "0.5", "0.75", "1", "2", "3", "5", "10", "15"]
		for doctype in ("Item", "Item Group"):
			meta = frappe.get_meta(doctype, cached=False)
			self.assertEqual(
				meta.get_field("custom_thai_withholding_tax_income_type").options,
				"Thai Withholding Tax Income Type",
			)
			rate = meta.get_field("custom_thai_withholding_tax_rate")
			self.assertEqual(rate.fieldtype, "Select")
			self.assertEqual(rate.options.split("\n"), rate_options)
			rate_by_category = meta.get_field("custom_thai_withholding_tax_rate_by_category")
			self.assertEqual(rate_by_category.fieldtype, "Table")
			self.assertEqual(rate_by_category.options, "Thai Withholding Tax Rate by Category")
			field_order = [field.fieldname for field in meta.fields]
			self.assertEqual(
				field_order.index("custom_thai_withholding_tax_rate_by_category"),
				field_order.index("custom_thai_withholding_tax_rate") + 1,
			)

		item_meta = frappe.get_meta("Item", cached=False)
		self.assertTrue(item_meta.get_field("purchase_tax_withholding_category").hidden)
		self.assertTrue(item_meta.get_field("sales_tax_withholding_category").hidden)

	def test_initial_data_is_complete_and_idempotent(self):
		category_doctype = "Thai Withholding Tax Category"
		income_type_doctype = "Thai Withholding Tax Income Type"
		expected_income_types = {
			"1 เงินเดือนค่าจ้าง เบี้ยเลี้ยง",
			"2 ค่าธรรมเนียม ค่านายหน้า",
			"3 ค่าแห่งลิขสิทธิ์",
			"4 ก ดอกเบี้ย",
			"4 ข เงินปันผล",
			"4 อื่นๆ",
			"5 ค่าเช่า",
			"6 เงินได้จากวิชาชีพอิสระ",
			"7 การรับเหมาที่ผู้รับเหมาต้องลงทุนด้วยการจัดหาสัมภาระ",
			"8 อื่นๆ",
		}

		report = SetupInitialData().make()
		self.assertEqual(report["created"], {})
		self.assertEqual(report["updated"], {})
		self.assertEqual(len(report["skipped"][category_doctype]), 5)
		self.assertEqual(len(report["skipped"][income_type_doctype]), 10)
		self.assertSetEqual(
			set(frappe.get_all(income_type_doctype, pluck="name")),
			expected_income_types,
		)

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

	@patch(
		"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_cached_value"
	)
	@patch("erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_cached_doc")
	@patch("erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_doc")
	def test_fetch_wht_detail_uses_category_and_keeps_defaults_at_one_level(
		self, get_doc, get_cached_doc, get_cached_value
	):
		item = frappe._dict(
			name="ITEM-1",
			custom_thai_withholding_tax_income_type="Item Income",
			custom_thai_withholding_tax_rate=0,
			custom_thai_withholding_tax_rate_by_category=[],
			item_group="Services",
			check_permission=MagicMock(),
		)
		item_income = frappe._dict(
			default_thai_withholding_tax_rate="5",
			thai_withholding_tax_rate_by_category=[
				frappe._dict(thai_withholding_tax_category="Juristic", rate="2")
			],
		)
		item_group = frappe._dict(
			custom_thai_withholding_tax_income_type="Group Income",
			custom_thai_withholding_tax_rate=3.5,
			custom_thai_withholding_tax_rate_by_category=[],
		)
		group_income = frappe._dict(
			default_thai_withholding_tax_rate="10",
			thai_withholding_tax_rate_by_category=[],
		)
		get_doc.return_value = item
		get_cached_doc.side_effect = lambda doctype, name: {
			("Item Group", "Services"): item_group,
			("Thai Withholding Tax Income Type", "Item Income"): item_income,
			("Thai Withholding Tax Income Type", "Group Income"): group_income,
		}[(doctype, name)]
		get_cached_value.side_effect = lambda doctype, name, fieldname: {
			("Supplier", "SUP-1"): "Individual",
			("Company", "Company A"): "Juristic",
		}[(doctype, name)]

		self.assertEqual(
			fetch_wht_detail("ITEM-1"),
			{"income_type": "Item Income", "tax_rate": 0.0, "source": "Item"},
		)

		item.custom_thai_withholding_tax_rate = ""
		self.assertEqual(
			fetch_wht_detail("ITEM-1", "Customer", "CUS-1", "Company A"),
			{"income_type": "Item Income", "tax_rate": 2.0, "source": "Item"},
		)

		item.custom_thai_withholding_tax_rate_by_category = [
			frappe._dict(thai_withholding_tax_category="Individual", rate="1")
		]
		self.assertEqual(
			fetch_wht_detail("ITEM-1", "Supplier", "SUP-1", "Company A"),
			{"income_type": "Item Income", "tax_rate": 1.0, "source": "Item"},
		)

		item.custom_thai_withholding_tax_income_type = None
		self.assertEqual(
			fetch_wht_detail("ITEM-1"),
			{"income_type": "Group Income", "tax_rate": 3.5, "source": "Item Group"},
		)

		item_group.custom_thai_withholding_tax_income_type = None
		self.assertEqual(fetch_wht_detail("ITEM-1"), {"income_type": None, "tax_rate": 0, "source": None})
		item.check_permission.assert_called_with("read")

	def test_applies_thai_withholding_tax_to_invoice_payment_entries(self):
		for invoice_doctype, payment_type, expected_amount, account_field in (
			("Sales Invoice", "Receive", 3, "sales_withholding_tax_account"),
			("Purchase Invoice", "Pay", -3, "purchase_withholding_tax_pnd53_account"),
		):
			payment_entry, invoice = self.make_invoice_payment_entry(invoice_doctype, payment_type)

			def get_cached_value(doctype, name, fieldname):
				if fieldname == "custom_thai_withholding_tax_category":
					return "Juristic"
				if doctype == "Company" and fieldname == account_field:
					return "Withholding Tax Account - TC"
				return None

			db_get_value = frappe.db.get_value

			def get_value(doctype, *args, **kwargs):
				if doctype == "Thai Withholding Tax Category Pnd":
					return "PND 53"
				return db_get_value(doctype, *args, **kwargs)

			with (
				patch(
					"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.fetch_wht_detail",
					return_value={"income_type": "Service", "tax_rate": 3, "source": "Item"},
				),
				patch(
					"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_cached_value",
					side_effect=get_cached_value,
				),
				patch(
					"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.db.get_value",
					side_effect=get_value,
				),
			):
				apply_thai_withholding_tax(payment_entry, invoice)

			self.assertEqual(payment_entry.paid_amount, 104)
			self.assertEqual(payment_entry.received_amount, 104)
			self.assertEqual(payment_entry.deductions[0].account, "Withholding Tax Account - TC")
			self.assertEqual(payment_entry.deductions[0].amount, expected_amount)
			self.assertEqual(payment_entry.difference_amount, 0)

	def test_applies_withholding_tax_in_proportion_to_payment(self):
		payment_entry, invoice = self.make_invoice_payment_entry("Sales Invoice", "Receive")
		payment_entry.references[0].allocated_amount = 53.5
		payment_entry.paid_amount = payment_entry.received_amount = 53.5

		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.fetch_wht_detail",
				return_value={"income_type": "Service", "tax_rate": 3, "source": "Item Group"},
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_cached_value",
				return_value="Withholding Tax Account - TC",
			),
		):
			apply_thai_withholding_tax(payment_entry, invoice)

		self.assertEqual(payment_entry.paid_amount, 52)
		self.assertEqual(payment_entry.received_amount, 52)
		self.assertEqual(payment_entry.deductions[0].amount, 1.5)
		self.assertEqual(payment_entry.difference_amount, 0)

	def test_requires_withholding_tax_account(self):
		payment_entry, invoice = self.make_invoice_payment_entry("Sales Invoice", "Receive")
		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.fetch_wht_detail",
				return_value={"income_type": "Service", "tax_rate": 3, "source": "Item"},
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.withholding_tax.frappe.get_cached_value",
				return_value=None,
			),
			self.assertRaisesRegex(frappe.ValidationError, "Sales Withholding Tax Account"),
		):
			apply_thai_withholding_tax(payment_entry, invoice)

	def make_invoice_payment_entry(self, invoice_doctype, payment_type):
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.update(
			{
				"company": "Test Company",
				"cost_center": "Test Cost Center - TC",
				"payment_type": payment_type,
				"paid_from_account_currency": "THB",
				"paid_to_account_currency": "THB",
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"paid_amount": 107,
				"received_amount": 107,
			}
		)
		payment_entry.append(
			"references",
			{
				"reference_doctype": invoice_doctype,
				"reference_name": "INV-0001",
				"allocated_amount": 107,
				"exchange_rate": 1,
			},
		)
		invoice = frappe._dict(
			doctype=invoice_doctype,
			name="INV-0001",
			customer="Customer A",
			supplier="Supplier A",
			company_currency="THB",
			base_grand_total=107,
			grand_total=107,
			items=[frappe._dict(item_code="SERVICE", base_net_amount=100)],
		)
		return payment_entry, invoice

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
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.get_doc",
				side_effect=get_doc,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.has_permission",
				return_value=True,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.get_mapped_doc",
				side_effect=map_doc,
			),
		):
			target = mapper(source.name)

		self.assertEqual(target.company, source.company)
		self.assertEqual(target.company_currency, "THB")
		self.assertEqual(target.payment_date, source.posting_date)
		self.assertEqual(target.get(party_field), party)
		self.assertEqual(target.get(address_field), "Address A")
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
					"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.get_doc",
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
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.get_doc",
				return_value=source,
			),
			self.assertRaises(frappe.PermissionError),
		):
			make_purchase_withholding_tax_entry(source.name)

		source.check_permission = MagicMock()
		with (
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.get_doc",
				return_value=source,
			),
			patch(
				"erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.frappe.has_permission",
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

	def test_reference_integrity(self):
		doc = frappe.new_doc("Purchase Withholding Tax Entry")
		item = frappe._dict(idx=1)

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
