// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Purchase Withholding Tax Entry", {
	setup(frm) {
		frm.set_query("supplier_address", () => ({
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: { link_doctype: "Supplier", link_name: frm.doc.supplier },
		}));
		frm.set_query("income_type", "items", () => ({ filters: { disabled: 0 } }));
		frm.set_query("gl_entry", "items", () => {
			const filters = { company: frm.doc.company, is_cancelled: 0 };
			if (frm.doc.payment_entry) {
				filters.voucher_type = "Payment Entry";
				filters.voucher_no = frm.doc.payment_entry;
			}
			return { filters };
		});
	},
	items_remove(frm) {
		frm.set_value({
			total_base_amount: (frm.doc.items || []).reduce(
				(total, row) => total + flt(row.base_amount),
				0
			),
			total_tax_amount: (frm.doc.items || []).reduce(
				(total, row) => total + flt(row.tax_amount),
				0
			),
		});
	},
});
