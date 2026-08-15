// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

/* global erpnext */

frappe.provide("erpnext.utils");

frappe.ui.form.on("Sales Withholding Tax Entry", {
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
		frm.set_query("customer_address", () => ({
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: { link_doctype: "Customer", link_name: frm.doc.customer },
		}));
		frm.set_query("income_type", "items", () => ({ filters: { disabled: 0 } }));
	},

	add_get_items_from_payment_entry_button(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.company) {
			frm.add_custom_button(
				__("Payment Entry"),
				() => frm.trigger("get_items_from_payment_entry"),
				__("Get Items From")
			);
		}
	},

	get_items_from_payment_entry(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry.make_sales_withholding_tax_entry",
			source_doctype: "Payment Entry",
			target: frm,
			date_field: "posting_date",
			setters: [
				{
					fieldname: "company",
					fieldtype: "Link",
					label: __("Company"),
					options: "Company",
					default: frm.doc.company,
					read_only: 1,
				},
				{
					fieldname: "party",
					fieldtype: "Link",
					label: __("Customer"),
					options: "Customer",
					default: frm.doc.customer || undefined,
					read_only: Boolean(frm.doc.customer),
				},
			],
			get_query_filters: {
				docstatus: 1,
				payment_type: "Receive",
				party_type: "Customer",
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
