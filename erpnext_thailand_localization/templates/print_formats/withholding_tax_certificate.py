from collections import OrderedDict
from decimal import Decimal

import frappe
from frappe.utils import getdate
from num2words import num2words


def certificate_rows(items):
	"""Combine entry amounts into the certificate's income rows."""
	rows = OrderedDict()
	for item in items:
		income = item.income_type or ""
		if income.startswith(("1 ", "2 ", "3 ")):
			key = income[0]
		elif income.startswith("4 ก"):
			key = "interest"
		elif income.startswith(("5 ", "6 ", "7 ", "8 ")):
			key = "services"
		else:
			# Dividend credit details are not recorded on the entry.
			key = "other"
		row = rows.setdefault(key, frappe._dict(base=Decimal(0), tax=Decimal(0), descriptions=[]))
		row.base += Decimal(str(item.base_amount or 0))
		row.tax += Decimal(str(item.tax_amount or 0))
		if income and income not in row.descriptions:
			row.descriptions.append(income)
	return rows


def certificate_address(address_name):
	"""Return plain address text without HTML from an address template."""
	if not address_name:
		return ""
	address = frappe.get_doc("Address", address_name)
	return " ".join(
		str(address.get(field))
		for field in ("address_line1", "address_line2", "city", "county", "state", "pincode")
		if address.get(field)
	)


def purchase_withholding_certificate(doc):
	"""Adapt purchase data to the shared certificate template context."""
	company = frappe.get_doc("Company", doc.company)
	supplier = frappe.get_doc("Supplier", doc.supplier)
	addresses = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Company", "link_name": doc.company},
		pluck="parent",
	)
	company_address = (
		frappe.get_all(
			"Address",
			filters={"name": ["in", addresses], "disabled": 0},
			order_by="is_primary_address desc, name asc",
			pluck="name",
			limit=1,
		)
		if addresses
		else []
	)
	date = getdate(doc.payment_date) if doc.payment_date else None
	return frappe._dict(
		number=doc.name,
		total_base_amount=doc.total_base_amount or 0,
		total_tax_amount=doc.total_tax_amount or 0,
		pnd_types={doc.pnd} if doc.pnd else set(),
		payer=company.company_name or company.name,
		payer_tax_id="".join(c for c in (company.tax_id or "") if c.isdigit()),
		payer_address=certificate_address(company_address[0] if company_address else None),
		recipient=supplier.supplier_name or supplier.name,
		recipient_tax_id="".join(c for c in (supplier.tax_id or "") if c.isdigit()),
		recipient_address=certificate_address(doc.supplier_address),
		date=f"{date.day:02d}/{date.month:02d}/{date.year + 543}" if date else "",
		rows=certificate_rows(doc.items),
		tax_words=num2words(Decimal(str(doc.total_tax_amount or 0)), lang="th", to="currency"),
	)
