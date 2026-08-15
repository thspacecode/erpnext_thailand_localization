// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

/* global erpnext */

frappe.provide("erpnext.utils");

frappe.ui.form.on("Purchase Withholding Tax Entry", {
	setup(frm) {
		frm.trigger("set_queries");
	},

	refresh(frm) {
		frm.trigger("add_get_items_from_payment_entry_button");
	},

	items_remove(frm) {
		frm.trigger("calculate_totals");
	},

	set_queries(frm) {
		frm.set_query("supplier_address", () => ({
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: { link_doctype: "Supplier", link_name: frm.doc.supplier },
		}));
		frm.set_query("income_type", "items", () => ({ filters: { disabled: 0 } }));
	},

	add_get_items_from_payment_entry_button(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.company && frm.doc.supplier) {
			frm.add_custom_button(
				__("Payment Entry"),
				() => frm.trigger("get_items_from_payment_entry"),
				__("Get Items From")
			);
		}
	},

	get_items_from_payment_entry(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry.make_purchase_withholding_tax_entry",
			source_doctype: "Payment Entry",
			target: frm,
			date_field: "posting_date",
			setters: {
				company: frm.doc.company || undefined,
				party: frm.doc.supplier || undefined,
			},
			read_only_setters: ["company", "party"],
			get_query_filters: {
				docstatus: 1,
				payment_type: "Pay",
				party_type: "Supplier",
				company: frm.doc.company,
				party: frm.doc.supplier,
			},
		});
	},

	calculate_totals(frm) {
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
