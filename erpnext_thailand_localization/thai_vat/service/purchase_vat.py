import frappe
from frappe import _
from frappe.utils import flt


def get_purchase_vat_rows(doc, taxes, *, tax_invoice_number, tax_invoice_date, report_date):
	"""Use final company-currency amounts for supported net-total purchase VAT rows."""
	rows = []
	for tax in taxes:
		if not flt(tax.base_tax_amount_after_discount_amount):
			continue
		if (
			tax.charge_type != "On Net Total"
			or tax.category != "Total"
			or tax.add_deduct_tax != "Add"
			or flt(tax.rate) <= 0
		):
			frappe.throw(_("Purchase VAT conversion requires added On Net Total VAT in the Total category."))
		base = flt(doc.base_net_total)
		if flt(tax.base_tax_amount):
			base *= flt(tax.base_tax_amount_after_discount_amount) / flt(tax.base_tax_amount)
		amount = flt(tax.base_tax_amount_after_discount_amount)
		if abs(flt(base * flt(tax.rate) / 100, 2) - amount) > 0.02:
			frappe.throw(_("Purchase VAT conversion requires a uniform VAT rate on the invoice net total."))
		rows.append(
			{
				"direction": "Purchase",
				"party": doc.supplier,
				"tax_invoice_number": tax_invoice_number,
				"tax_invoice_date": tax_invoice_date,
				"report_date": report_date,
				"vat_category": "Taxable",
				"rate": tax.rate,
				"tax_base": flt(base, 2),
				"tax_amount": amount,
				"source_identity": tax.name,
				"undue_vat_account": tax.account_head,
				"conversion_cost_center": tax.get("cost_center") or doc.get("cost_center"),
			}
		)
	return rows
