frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (
			frm.doc.payment_type === "Pay" &&
			frm.doc.party_type === "Supplier" &&
			frappe.model.can_create("Purchase Withholding Tax Entry")
		) {
			frm.add_custom_button(
				__("Purchase Withholding Tax Entry"),
				() =>
					frappe.model.open_mapped_doc({
						method: "erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry.make_purchase_withholding_tax_entry",
						frm,
					}),
				__("Create")
			);
		}

		if (
			frm.doc.payment_type === "Receive" &&
			frm.doc.party_type === "Customer" &&
			frappe.model.can_create("Sales Withholding Tax Entry")
		) {
			frm.add_custom_button(
				__("Sales Withholding Tax Entry"),
				() =>
					frappe.model.open_mapped_doc({
						method: "erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry.make_sales_withholding_tax_entry",
						frm,
					}),
				__("Create")
			);
		}
	},
});
