// Copyright (c) 2026, SpaceCode Co., Ltd. and contributors
// For license information, please see license.txt

/* global erpnext */

frappe.ui.form.on("Journal Entry", {
	refresh(frm) {
		frm.trigger("add_get_pnd_filing_buttons");
	},

	add_get_pnd_filing_buttons(frm) {
		if (frm.doc.docstatus !== 0) {
			return;
		}

		const filing_types = [
			{
				label: __("PND 3 Filing"),
				doctype: "Thai PND 3 Filing",
				method: "erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_3_filing.thai_pnd_3_filing.make_journal_entry",
			},
			{
				label: __("PND 53 Filing"),
				doctype: "Thai PND 53 Filing",
				method: "erpnext_thailand_localization.thai_withholding_tax.doctype.thai_pnd_53_filing.thai_pnd_53_filing.make_journal_entry",
			},
		];

		filing_types.forEach((filing_type) => {
			if (!frappe.model.can_read(filing_type.doctype)) {
				return;
			}

			frm.add_custom_button(
				filing_type.label,
				() =>
					erpnext.utils.map_current_doc({
						method: filing_type.method,
						source_doctype: filing_type.doctype,
						target: frm,
						setters: [
							{
								fieldname: "company",
								fieldtype: "Link",
								label: __("Company"),
								options: "Company",
								default: frm.doc.company,
							},
						],
						get_query_filters: {
							docstatus: 1,
							...(frm.doc.company ? { company: frm.doc.company } : {}),
						},
					}),
				__("Get Item From")
			);
		});
	},
});
