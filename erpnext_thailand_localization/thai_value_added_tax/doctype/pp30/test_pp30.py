from decimal import Decimal

import frappe

from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite


class TestPP30(ERPNextThaiTestSuite):
	def test_calculate_amounts(self):
		"""Calculate normal-filing VAT and apply prior-period credit without a fixed tax rate."""
		# Arrange: Sales contain 200 zero-rated and 100 exempt; credit is 10.
		doc = frappe.get_doc(
			doctype="PP30",
			sales_amount=1000,
			zero_rated_sales=200,
			exempt_sales=100,
			output_vat=49,
			input_vat=20,
			carried_forward_credit=10,
		)
		# Act and assert: Taxable sales are 700; net payable is 49 - 20 - 10.
		doc.calculate_amounts()
		self.assertEqual(doc.taxable_sales, Decimal("700.00"))
		self.assertEqual(doc.vat_payable, Decimal("19.00"))
		self.assertEqual(doc.excess_vat, 0)
		doc.input_vat = 60
		doc.calculate_amounts()
		self.assertEqual(doc.excess_vat_before_credit, Decimal("11.00"))
		self.assertEqual(doc.excess_vat, Decimal("21.00"))
		self.assertEqual(doc.vat_payable, 0)

	def test_branch_totals(self):
		"""Sum branch amounts and reject equivalent branch numbers with different padding."""
		# Arrange: Two branch rows replace a stale parent sales value.
		doc = frappe.get_doc(
			doctype="PP30",
			use_branch_totals=1,
			sales_amount=999,
			branches=[
				dict(
					branch_no="00000",
					address_number="1",
					postal_code="10110",
					sales_amount=100,
					output_vat=7,
					input_vat=2,
				),
				dict(
					branch_no="00001",
					address_number="2",
					postal_code="10110",
					sales_amount=200,
					output_vat=14,
					input_vat=3,
				),
			],
		)
		# Act and assert: Sum the rows, then reject a duplicate numeric branch.
		doc.calculate_amounts()
		self.assertEqual(doc.sales_amount, Decimal("300.00"))
		self.assertEqual(doc.vat_payable, Decimal("16.00"))
		doc.branches[1].branch_no = "0"
		with self.assertRaisesRegex(frappe.ValidationError, "Branch Number must not repeat"):
			doc.calculate_amounts()

	def test_invalid_amounts(self):
		"""Reject negative amounts and sales categories that exceed total sales."""
		# Arrange: A valid baseline uses entered VAT amounts.
		doc = frappe.get_doc(doctype="PP30", sales_amount=100, zero_rated_sales=20)
		doc.calculate_amounts()
		# Act and assert: Change one condition at a time.
		doc.output_vat = -1
		with self.assertRaisesRegex(frappe.ValidationError, "finite, non-negative"):
			doc.calculate_amounts()
		doc.output_vat = 0
		doc.zero_rated_sales = 101
		with self.assertRaisesRegex(frappe.ValidationError, "must not exceed monthly sales"):
			doc.calculate_amounts()

	def test_validate_taxpayer(self):
		"""Require an explicit Buddhist Era year and numeric taxpayer identifiers."""
		# Arrange: Validate identifiers without creating Company master data.
		doc = frappe.get_doc(doctype="PP30", tax_id="0105551234567", tax_year=2569, branch_no="00000")
		doc.validate_taxpayer()
		# Act and assert: A Gregorian year must not be silently reinterpreted.
		doc.tax_year = 2026
		with self.assertRaisesRegex(frappe.ValidationError, "Buddhist Era"):
			doc.validate_taxpayer()

	def test_calculate_from_entries(self):
		"""Use submitted entry values, including credit notes, rather than manual totals."""
		from unittest.mock import patch

		doc = frappe.get_doc(
			doctype="PP30",
			company="Example",
			company_tax_address="Office",
			tax_id="0105551234567",
			branch_no="00000",
			tax_year=2569,
			tax_month="01",
			purchase_entries=[dict(vat_entry="P1")],
			sales_entries=[dict(vat_entry="S1"), dict(vat_entry="S2")],
		)

		def entry(doctype, name, **kwargs):
			"""Build source entries in memory; database lookup and permissions are mocked."""
			return frappe.get_doc(
				doctype=doctype,
				name=name,
				docstatus=1,
				company="Example",
				company_tax_address="Office",
				company_currency="THB",
				company_tax_id="0105551234567",
				company_branch_code="00000",
				party_name="Invoice Party",
				tax_invoice_number=name,
				tax_invoice_date="2026-01-15",
				tax_id="0105557654321",
				branch_code="00000",
				report_date="2026-01-15",
				vat_category="Taxable",
				**kwargs,
			)

		purchase = entry("Purchase VAT Entry", "P1", tax_base=500, tax_amount=35)
		sale = entry("Sales VAT Entry", "S1", tax_base=1000, tax_amount=70)
		credit = entry("Sales VAT Entry", "S2", tax_base=-100, tax_amount=-7)
		entries = {"P1": purchase, "S1": sale, "S2": credit}
		# Act and assert: Run real selection validation and arithmetic with mocked source reads.
		with (
			patch("frappe.get_doc", side_effect=lambda dt, name, **kw: entries[name]),
			patch.object(type(purchase), "check_permission"),
			patch.object(type(sale), "check_permission"),
			patch.object(doc, "get_other_return", return_value=None),
		):
			doc.calculate_from_entries()
			self.assertEqual(doc.sales_amount, Decimal("900.00"))
			self.assertEqual(doc.input_vat, Decimal("35.00"))
			self.assertEqual(doc.vat_payable, Decimal("28.00"))
			sale.docstatus = 0
			with self.assertRaisesRegex(frappe.ValidationError, "Only submitted VAT Entries"):
				doc.calculate_from_entries()
			sale.docstatus = 1
			sale.report_date = "2026-02-01"
			with self.assertRaisesRegex(frappe.ValidationError, "reporting period"):
				doc.calculate_from_entries()
			sale.report_date = "2026-01-15"
			doc.append("sales_entries", dict(vat_entry="S1"))
			with self.assertRaisesRegex(frappe.ValidationError, "only once"):
				doc.calculate_from_entries()

	def test_get_other_return(self):
		"""Ignore the current return when checking submitted allocations."""
		from unittest.mock import patch

		doc = frappe.get_doc(doctype="PP30", name="PP30-1")
		# Arrange and assert: The current parent alone is not a conflicting return.
		with patch("frappe.get_all", return_value=["PP30-1"]), patch("frappe.db.exists") as exists:
			self.assertIsNone(doc.get_other_return("Purchase VAT Entry", "P1"))
			exists.assert_not_called()

	def test_get_vat_entries(self):
		"""Replace draft selection with permitted period entries not already filed."""
		from unittest.mock import patch

		doc = frappe.get_doc(
			doctype="PP30",
			company="Example",
			company_tax_address="Office",
			tax_year=2569,
			tax_month="01",
			purchase_entries=[dict(vat_entry="OLD")],
		)
		# Arrange: Mock source search and arithmetic to isolate the selection method.
		with (
			patch.object(doc, "check_permission"),
			patch.object(doc, "set_company_details"),
			patch.object(doc, "calculate_from_entries"),
			patch.object(doc, "get_other_return", side_effect=[None, "OTHER"]),
			patch("frappe.get_list", side_effect=[[frappe._dict(name="P1"), frappe._dict(name="P2")], []]),
		):
			doc.get_vat_entries()
			self.assertEqual([row.vat_entry for row in doc.purchase_entries], ["P1"])
			self.assertEqual(doc.sales_entries, [])
			doc.docstatus = 1
			with self.assertRaisesRegex(frappe.ValidationError, "only be loaded into a draft"):
				doc.get_vat_entries()

	def test_render_vat_register(self):
		"""Print stored invoice details with escaping instead of reading current party masters."""
		from unittest.mock import patch

		doc = frappe.get_doc(
			doctype="PP30", name="PP30-PRINT", tax_year=2569, tax_month="01", branch_no="00000"
		)
		entry = frappe._dict(
			company_taxpayer_name="Company",
			company_tax_id="0105551234567",
			company_address_display="Stored Address",
			tax_invoice_date="2026-01-15",
			tax_invoice_number="INV-1",
			tax_invoice_book="B1",
			party_name="Stored <Supplier>",
			tax_id="0105557654321",
			branch_code="00000",
			tax_base=100,
			tax_amount=7,
		)
		# Act and assert: Mock the selected records only; render the actual template.
		with patch.object(doc, "get_report_entries", new=lambda table: [entry]):
			html = frappe.render_template(
				"erpnext_thailand_localization/templates/print_formats/documents/vat_register.html.jinja",
				dict(doc=doc, entry_table="purchase_entries"),
				is_path=True,
			)
			self.assertIn("Stored &lt;Supplier&gt;", html)
			self.assertIn("INV-1", html)
			self.assertIn("Stored Address", html)
