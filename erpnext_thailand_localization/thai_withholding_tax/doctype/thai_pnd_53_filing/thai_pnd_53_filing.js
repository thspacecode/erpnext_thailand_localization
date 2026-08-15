// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Thai PND 53 Filing", {
	setup(frm) {
		frm.trigger("set_queries");
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

	add_get_withholding_tax_entries_button(frm) {
		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.company && frm.doc.tax_period) {
			frm.add_custom_button(__("Get Withholding Tax Entries"), () =>
				frm.trigger("get_items")
			);
		}
	},

	clear_company_address(frm) {
		if (frm.doc.company_address) {
			frm.set_value("company_address", null);
		}
	},

	get_items(frm) {
		frappe.call({
			method: "erpnext_thailand_localization.thai_withholding_tax.service.pnd_filing.get_eligible_items",
			args: {
				return_doctype: frm.doc.doctype,
				company: frm.doc.company,
				tax_period: frm.doc.tax_period,
			},
			freeze: true,
			freeze_message: __("Getting withholding tax entries..."),
			callback(r) {
				frm.clear_table("items");
				(r.message || []).forEach((item) => frm.add_child("items", item));
				frm.refresh_field("items");
				frm.trigger("calculate_totals");
				if (!r.message?.length) {
					frappe.msgprint(
						__("No eligible submitted withholding tax entries were found.")
					);
				}
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
});
