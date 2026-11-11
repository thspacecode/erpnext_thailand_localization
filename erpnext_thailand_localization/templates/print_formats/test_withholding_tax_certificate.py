import unittest
from decimal import Decimal

import frappe

from erpnext_thailand_localization.templates.print_formats.withholding_tax_certificate import certificate_rows


class TestCertificateRows(unittest.TestCase):
	def test_certificate_rows(self):
		"""Group service income and preserve decimal tax totals."""
		items = [
			frappe._dict(income_type="5 ค่าเช่า", base_amount=100.1, tax_amount=3.01),
			frappe._dict(income_type="8 อื่นๆ", base_amount=200.2, tax_amount=6.01),
			frappe._dict(income_type="1 เงินเดือน", base_amount=1000, tax_amount=10),
		]
		rows = certificate_rows(items)
		self.assertEqual(rows["services"].base, Decimal("300.3"))
		self.assertEqual(rows["services"].tax, Decimal("9.02"))
		self.assertEqual(rows["1"].base, Decimal("1000"))
		self.assertEqual(len(rows["services"].descriptions), 2)

	def test_certificate_rows_income_sections(self):
		"""Keep interest and other income separate from service income."""
		items = [
			frappe._dict(income_type="4 ก ดอกเบี้ย", base_amount=1000.25, tax_amount=150.04),
			frappe._dict(income_type="4 อื่นๆ", base_amount=2000.50, tax_amount=200.05),
		]
		rows = certificate_rows(items)
		self.assertEqual(set(rows), {"interest", "other"})
		self.assertEqual(rows["interest"].tax, Decimal("150.04"))
		self.assertEqual(rows["other"].descriptions, ["4 อื่นๆ"])
