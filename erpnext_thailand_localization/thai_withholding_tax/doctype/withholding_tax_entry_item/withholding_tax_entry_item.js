// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

function calculate_wht_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.tax_amount = flt(
		(flt(row.base_amount) * flt(row.tax_rate)) / 100,
		precision("tax_amount", row)
	);
	frm.refresh_field("items");
	calculate_wht_totals(frm);
}

function calculate_wht_totals(frm) {
	const total_base_amount = (frm.doc.items || []).reduce(
		(total, row) => total + flt(row.base_amount),
		0
	);
	const total_tax_amount = (frm.doc.items || []).reduce(
		(total, row) => total + flt(row.tax_amount),
		0
	);
	frm.set_value({ total_base_amount, total_tax_amount });
}

frappe.ui.form.on("Withholding Tax Entry Item", {
	base_amount: calculate_wht_row,
	tax_rate: calculate_wht_row,
});
