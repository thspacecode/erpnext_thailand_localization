frappe.ui.form.on("Payment Entry", {
	async refresh(frm) {
		await frm.trigger("toggle_withholding_tax_entry_buttons");
	},

	dashboard_update(frm) {
		frm.trigger("toggle_withholding_tax_dashboard_buttons");
	},

	toggle_withholding_tax_dashboard_buttons(frm) {
		const linked_doctypes = (frm.dashboard_data?.count?.external_links_found || [])
			.filter((link) => link.count > 0)
			.map((link) => link.doctype);
		const allowed_doctype =
			frm.doc.payment_type === "Receive"
				? "Sales Withholding Tax Entry"
				: frm.doc.payment_type === "Pay"
				? "Purchase Withholding Tax Entry"
				: null;

		for (const doctype of ["Sales Withholding Tax Entry", "Purchase Withholding Tax Entry"]) {
			if (doctype !== allowed_doctype || linked_doctypes.includes(doctype)) {
				frm.dashboard.transactions_area
					.find(`.btn-new[data-doctype="${doctype}"]`)
					.addClass("hidden");
			}
		}
	},

	async toggle_withholding_tax_entry_buttons(frm) {
		const can_create_purchase_entry =
			frm.doc.docstatus === 1 &&
			frm.doc.payment_type === "Pay" &&
			frm.doc.party_type === "Supplier" &&
			frappe.model.can_create("Purchase Withholding Tax Entry");
		const can_create_sales_entry =
			frm.doc.docstatus === 1 &&
			frm.doc.payment_type === "Receive" &&
			frm.doc.party_type === "Customer" &&
			frappe.model.can_create("Sales Withholding Tax Entry");

		if (!can_create_purchase_entry && !can_create_sales_entry) {
			return;
		}

		const { message: has_existing_entry } = await frappe.call({
			method: "erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.has_existing_withholding_tax_entry",
			args: { payment_entry: frm.doc.name },
		});
		if (has_existing_entry) {
			return;
		}

		frm.trigger("add_purchase_withholding_tax_entry_button");
		frm.trigger("add_sales_withholding_tax_entry_button");
	},

	async custom_get_withholding_tax_from_references(frm) {
		await frm.trigger("get_withholding_tax_from_references");
	},

	add_purchase_withholding_tax_entry_button(frm) {
		if (
			frm.doc.docstatus === 1 &&
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
	},

	add_sales_withholding_tax_entry_button(frm) {
		if (
			frm.doc.docstatus === 1 &&
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

	async get_withholding_tax_from_references(frm) {
		const has_existing_withholding_tax = (frm.doc.deductions || []).some(
			(row) => row.custom_is_withholding_tax_entry
		);

		if (has_existing_withholding_tax) {
			const should_override = await new Promise((resolve) => {
				frappe.confirm(
					__(
						"This will override the existing withholding tax entries. Do you want to continue?"
					),
					() => resolve(true),
					() => resolve(false)
				);
			});

			if (!should_override) {
				return;
			}
		}

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
