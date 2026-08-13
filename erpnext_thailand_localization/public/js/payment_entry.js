frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		frm.toggle_display(
			"custom_get_withholding_tax_from_references",
			frm.doc.docstatus === 0 &&
				["Pay", "Receive"].includes(frm.doc.payment_type) &&
				(frm.doc.references || []).some((reference) => flt(reference.allocated_amount))
		);

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

	async custom_get_withholding_tax_from_references(frm) {
		const { message: deductions = [] } = await frappe.call({
			method: "erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.get_withholding_tax_from_references",
			args: { doc: frm.doc },
			freeze: true,
			freeze_message: __("Getting Withholding Tax from References..."),
		});

		const old_tax = (frm.doc.deductions || [])
			.filter((row) => row.custom_is_withholding_tax_entry)
			.reduce((total, row) => total + Math.abs(flt(row.amount)), 0);
		const new_tax = deductions.reduce((total, row) => total + Math.abs(flt(row.amount)), 0);

		for (const row of [...(frm.doc.deductions || [])]) {
			if (row.custom_is_withholding_tax_entry) {
				frappe.model.clear_doc(row.doctype, row.name);
			}
		}
		for (const deduction of deductions) {
			frm.add_child("deductions", deduction);
		}

		const tax_difference = new_tax - old_tax;
		frm.doc.paid_amount = flt(
			flt(frm.doc.paid_amount) - tax_difference / (flt(frm.doc.source_exchange_rate) || 1),
			precision("paid_amount")
		);
		frm.doc.received_amount = flt(
			flt(frm.doc.received_amount) -
				tax_difference / (flt(frm.doc.target_exchange_rate) || 1),
			precision("received_amount")
		);
		frm.doc.base_paid_amount = flt(
			frm.doc.paid_amount * flt(frm.doc.source_exchange_rate),
			precision("base_paid_amount")
		);
		frm.doc.base_received_amount = flt(
			frm.doc.received_amount * flt(frm.doc.target_exchange_rate),
			precision("base_received_amount")
		);
		frm.events.set_total_allocated_amount(frm);
		frm.refresh_fields();
		frm.dirty();

		if (deductions.length) {
			frappe.show_alert({
				message: __("Added {0} withholding tax deduction row(s).", [deductions.length]),
				indicator: "green",
			});
		} else {
			frappe.msgprint(__("No withholding tax was found in the selected references."));
		}
	},
});
