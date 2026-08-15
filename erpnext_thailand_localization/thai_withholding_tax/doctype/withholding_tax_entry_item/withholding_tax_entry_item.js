// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Withholding Tax Entry Item", {
	base_amount(frm, cdt, cdn) {
		frm.trigger("calculate_wht_row", cdt, cdn);
	},

	tax_rate(frm, cdt, cdn) {
		frm.trigger("calculate_wht_row", cdt, cdn);
	},

	calculate_wht_row(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.tax_amount = flt(
			(flt(row.base_amount) * flt(row.tax_rate)) / 100,
			precision("tax_amount", row)
		);
		frm.refresh_field("items");
		frm.trigger("calculate_wht_totals", cdt, cdn);
	},

	calculate_wht_totals(frm) {
		const total_base_amount = (frm.doc.items || []).reduce(
			(total, row) => total + flt(row.base_amount),
			0
		);
		const total_tax_amount = (frm.doc.items || []).reduce(
			(total, row) => total + flt(row.tax_amount),
			0
		);
		frm.set_value({ total_base_amount, total_tax_amount });
	},
});
