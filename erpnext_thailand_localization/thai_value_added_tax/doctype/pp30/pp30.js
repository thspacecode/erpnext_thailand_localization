// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("PP30", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get VAT Entries"), () => {
				frappe.confirm(__("Replace the current VAT entry selection?"), () => {
					frm.call("get_vat_entries").then(() => frm.refresh_fields());
				});
			});
		}
	},
});
