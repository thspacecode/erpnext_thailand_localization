frappe.ui.form.on("Payment Entry", {
	setup(frm) {
		frm.make_methods = {
			...(frm.make_methods || {}),
			"Sales Withholding Tax Entry": () => frm.trigger("open_sales_withholding_tax_entry"),
			"Purchase Withholding Tax Entry": () =>
				frm.trigger("open_purchase_withholding_tax_entry"),
		};
		frm.can_make_methods = {
			...(frm.can_make_methods || {}),
			"Sales Withholding Tax Entry": () =>
				frm.events.can_create_withholding_tax_entry(frm, "Sales Withholding Tax Entry") &&
				!frm.has_existing_withholding_tax_entry,
			"Purchase Withholding Tax Entry": () =>
				frm.events.can_create_withholding_tax_entry(
					frm,
					"Purchase Withholding Tax Entry"
				) && !frm.has_existing_withholding_tax_entry,
		};
	},

	can_create_withholding_tax_entry(frm, doctype) {
		const requirements = {
			"Sales Withholding Tax Entry": {
				payment_type: "Receive",
				party_type: "Customer",
			},
			"Purchase Withholding Tax Entry": {
				payment_type: "Pay",
				party_type: "Supplier",
			},
		}[doctype];

		return Boolean(
			requirements &&
				frm.doc.docstatus === 1 &&
				frm.doc.payment_type === requirements.payment_type &&
				frm.doc.party_type === requirements.party_type &&
				frappe.model.can_create(doctype)
		);
	},

	async refresh(frm) {
		await frm.trigger("toggle_withholding_tax_entry_buttons");
	},

	async toggle_withholding_tax_entry_buttons(frm) {
		frm.has_existing_withholding_tax_entry = false;

		const can_create_purchase_entry = frm.events.can_create_withholding_tax_entry(
			frm,
			"Purchase Withholding Tax Entry"
		);
		const can_create_sales_entry = frm.events.can_create_withholding_tax_entry(
			frm,
			"Sales Withholding Tax Entry"
		);

		if (!can_create_purchase_entry && !can_create_sales_entry) {
			return;
		}

		const { message: has_existing_entry } = await frappe.call({
			method: "erpnext_thailand_localization.thai_withholding_tax.service.payment_entry.has_existing_withholding_tax_entry",
			args: { payment_entry: frm.doc.name },
		});
		frm.has_existing_withholding_tax_entry = has_existing_entry;
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
		if (frm.events.can_create_withholding_tax_entry(frm, "Purchase Withholding Tax Entry")) {
			frm.add_custom_button(
				__("Purchase Withholding Tax Entry"),
				() => frm.make_new("Purchase Withholding Tax Entry"),
				__("Create")
			);
		}
	},

	add_sales_withholding_tax_entry_button(frm) {
		if (frm.events.can_create_withholding_tax_entry(frm, "Sales Withholding Tax Entry")) {
			frm.add_custom_button(
				__("Sales Withholding Tax Entry"),
				() => frm.make_new("Sales Withholding Tax Entry"),
				__("Create")
			);
		}
	},

	open_purchase_withholding_tax_entry(frm) {
		return frappe.model.open_mapped_doc({
			method: "erpnext_thailand_localization.thai_withholding_tax.doctype.purchase_withholding_tax_entry.purchase_withholding_tax_entry.make_purchase_withholding_tax_entry",
			frm,
		});
	},

	open_sales_withholding_tax_entry(frm) {
		return frappe.model.open_mapped_doc({
			method: "erpnext_thailand_localization.thai_withholding_tax.doctype.sales_withholding_tax_entry.sales_withholding_tax_entry.make_sales_withholding_tax_entry",
			frm,
		});
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
