// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

/* global erpnext, erpnext_thailand_localization */

frappe.provide("erpnext_thailand_localization.thai_withholding_tax");

erpnext_thailand_localization.thai_withholding_tax.pnd_filing = {
	setup(frm) {
		frm.trigger("set_queries");
	},

	onload(frm) {
		frm.trigger("set_default_tax_period");
	},

	refresh(frm) {
		frm.trigger("add_get_withholding_tax_entries_button");
	},

	company(frm) {
		frm.trigger("clear_company_address");
	},

	items_remove(frm) {
		frm.trigger("calculate_totals");
	},

	set_queries(frm) {
		frm.set_query("company_address", () => ({
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: { link_doctype: "Company", link_name: frm.doc.company },
		}));
	},

	set_default_tax_period(frm) {
		if (
			frm.is_new() &&
			(!frm.doc.tax_period || frm.doc.tax_period === frappe.datetime.get_today())
		) {
			frm.set_value("tax_period", frappe.datetime.month_start());
		}
	},

	add_get_withholding_tax_entries_button(frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}

		frm.add_custom_button(
			__("Purchase Withholding Tax Entry"),
			() => frm.trigger("get_items"),
			__("Get Items From")
		);
	},

	clear_company_address(frm) {
		if (frm.doc.company_address) {
			frm.set_value("company_address", null);
		}
	},

	get_items(frm) {
		if (!frm.doc.company || !frm.doc.tax_period) {
			frappe.msgprint(__("Please set Company and Tax Period first."));
			return;
		}

		erpnext.utils.map_current_doc({
			method: "erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing.add_purchase_withholding_tax_entry_to_filing",
			source_doctype: "Purchase Withholding Tax Entry",
			target: frm,
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
					fieldname: "payment_date",
					fieldtype: "Date Range",
					label: __("Payment Date"),
					default: [
						frm.doc.tax_period,
						frappe.datetime.add_days(
							frappe.datetime.add_months(frm.doc.tax_period, 1),
							-1
						),
					],
				},
				{
					fieldname: "supplier",
					fieldtype: "Link",
					label: __("Supplier"),
					options: "Supplier",
				},
			],
			get_query_method:
				"erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing.get_unfiled_purchase_withholding_tax_entries",
			get_query_filters: {
				return_doctype: frm.doc.doctype,
				company: frm.doc.company,
				tax_period: frm.doc.tax_period,
				docstatus: 1,
			},
		});
	},

	calculate_totals(frm) {
		const items = frm.doc.items || [];
		const recipients = new Set(
			items
				.filter((item) => item.recipient_tax_id)
				.map((item) => `${item.recipient_tax_id}:${item.recipient_branch_code || "00000"}`)
		);
		const total_tax_amount = items.reduce((total, item) => total + flt(item.tax_amount), 0);
		frm.set_value({
			recipient_count: recipients.size,
			attachment_page_count: recipients.size ? Math.ceil(recipients.size / 6) : 0,
			total_base_amount: items.reduce((total, item) => total + flt(item.base_amount), 0),
			total_tax_amount,
			grand_total: total_tax_amount + flt(frm.doc.surcharge_amount),
		});
	},
};
