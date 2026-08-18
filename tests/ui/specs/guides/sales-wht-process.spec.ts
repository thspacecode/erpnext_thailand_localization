import type { Page } from "@playwright/test";

import type { FrappeApi, FrappeDocument } from "../../fixtures/frappe-api";
import { expect, test } from "../../fixtures/test";
import { formatDeskDate } from "../../pages/desk.page";

const SALES_WHT_PROCESS = {
	customer: "Lackawanna County",
	item: "AUDIT-FEE",
	incomeType: "6 เงินได้จากวิชาชีพอิสระ",
	receivableAccount: "Sales Withholding Tax Receivable - DM",
	transactionDate: `${new Date().getUTCFullYear()}-01-15`,
	orderRates: [5_000, 8_000, 5_000],
} as const;

type SalesOrder = FrappeDocument & {
	grand_total: number;
};

type PaymentEntry = FrappeDocument & {
	base_paid_amount: number;
	base_received_amount: number;
	base_total_allocated_amount: number;
	deductions: Array<Record<string, unknown>>;
	difference_amount: number;
	paid_amount: number;
	received_amount: number;
	references: Array<Record<string, unknown>>;
	total_allocated_amount: number;
};

type PaymentEntrySummary = {
	deductions: Array<{
		account: string;
		amount: number;
		custom_base_amount: number;
		custom_income_type: string;
		custom_reference_document: string;
		custom_reference_document_type: string;
		custom_tax_rate: number;
	}>;
	paidAmount: number;
	references: Array<{
		allocated_amount: number;
		reference_doctype: string;
		reference_name: string;
	}>;
};

const transactionDateReplacement: [string, string] = [
	formatDeskDate(SALES_WHT_PROCESS.transactionDate),
	"15-01-20XX",
];

test.describe("Sales withholding tax process", () => {
	test("Creates withholding-tax deductions from sales orders", async ({
		api,
		desk,
		expectScreenshot,
		form,
		page,
	}, testInfo) => {
		testInfo.annotations.push({
			type: "prerequisite",
			description: "Set up Thai Withholding Tax and bootstrap the test master data.",
		});

		const salesOrders: SalesOrder[] = [];
		let draftPaymentEntry: PaymentEntry | undefined;

		try {
			for (const [index, rate] of SALES_WHT_PROCESS.orderRates.entries()) {
				salesOrders.push(await createSalesOrder(api, rate, index));
			}

			await test.step("Option A: open Payment Entry from a submitted Sales Order", async () => {
				const salesOrder = salesOrders[0];
				await page.setViewportSize({ width: 1440, height: 900 });
				await desk.goToDoc("Sales Order", salesOrder.name);
				expect(
					await page.evaluate(
						() =>
							(window as unknown as { cur_frm: { doc: { docstatus: number } } }).cur_frm.doc
								.docstatus,
					),
				).toBe(1);

				const createButton = page
					.locator(".page-head")
					.getByRole("button", { name: "Create", exact: true });
				await createButton.click();
				const paymentMenuItem = page
					.locator(".page-head .dropdown-menu:visible")
					.getByText(/^(Payment|Payment Entry)$/, { exact: true });
				await expect(paymentMenuItem).toBeVisible();

				await desk.normalizeDocumentNames([
					[salesOrder.name, "SAL-ORD-YYYY-00001"],
					transactionDateReplacement,
				]);
				await expectScreenshot("sales-order-create-payment-entry.png");

				await paymentMenuItem.click();
				await expect
					.poll(async () => (await desk.currentRoute()).slice(0, 2))
					.toEqual(["Form", "Payment Entry"]);
				await page.setViewportSize({ width: 1440, height: 1200 });

				const summary = await getPaymentEntrySummary(page);
				expect(summary.paidAmount).toBe(4_850);
				expect(summary.references).toEqual([
					expect.objectContaining({
						allocated_amount: 5_000,
						reference_doctype: "Sales Order",
						reference_name: salesOrder.name,
					}),
				]);
				expect(summary.deductions).toEqual([
					expect.objectContaining({
						account: SALES_WHT_PROCESS.receivableAccount,
						amount: 150,
						custom_base_amount: 5_000,
						custom_income_type: SALES_WHT_PROCESS.incomeType,
						custom_reference_document: salesOrder.name,
						custom_reference_document_type: "Sales Order",
						custom_tax_rate: 3,
					}),
				]);

				await showPaymentTables(page, form.field("references"), form.field("deductions"));
				await desk.normalizeDocumentNames([
					[salesOrder.name, "SAL-ORD-YYYY-00001"],
					transactionDateReplacement,
				]);
				await expectScreenshot("payment-entry-from-sales-order.png");
			});

			await test.step("Option B: get withholding tax from two Sales Order references", async () => {
				draftPaymentEntry = await createDraftPaymentEntry(api, salesOrders[1], salesOrders[2]);
				await page.setViewportSize({ width: 1440, height: 1200 });
				await desk.goToDoc("Payment Entry", draftPaymentEntry.name);

				const beforeSummary = await getPaymentEntrySummary(page);
				expect(beforeSummary.references).toHaveLength(2);
				expect(beforeSummary.deductions).toHaveLength(0);

				const getWithholdingTaxButton = form
					.field("custom_get_withholding_tax_from_references")
					.getByRole("button", { name: "Get Withholding Tax from References" });
				await expect(getWithholdingTaxButton).toBeVisible();

				await showPaymentTables(page, form.field("references"), form.field("deductions"));
				await desk.normalizeDocumentNames([
					[salesOrders[1].name, "SAL-ORD-YYYY-00002"],
					[salesOrders[2].name, "SAL-ORD-YYYY-00003"],
					transactionDateReplacement,
				]);
				await expectScreenshot("payment-entry-get-wht-from-references.png");

				await getWithholdingTaxButton.click();
				await expect
					.poll(async () => (await getPaymentEntrySummary(page)).deductions.length)
					.toBe(2);

				const afterSummary = await getPaymentEntrySummary(page);
				expect(afterSummary.paidAmount).toBe(12_610);
				expect(afterSummary.deductions).toEqual([
					expect.objectContaining({
						amount: 240,
						custom_base_amount: 8_000,
						custom_reference_document: salesOrders[1].name,
					}),
					expect.objectContaining({
						amount: 150,
						custom_base_amount: 5_000,
						custom_reference_document: salesOrders[2].name,
					}),
				]);

				await expect(page.locator(".alert-message")).toBeHidden({ timeout: 15_000 });
				await showPaymentTables(page, form.field("references"), form.field("deductions"));
				await desk.normalizeDocumentNames([
					[salesOrders[1].name, "SAL-ORD-YYYY-00002"],
					[salesOrders[2].name, "SAL-ORD-YYYY-00003"],
					transactionDateReplacement,
				]);
				await expectScreenshot("payment-entry-withholding-tax-from-references.png");
			});
		} finally {
			if (draftPaymentEntry) {
				await api.delete("Payment Entry", draftPaymentEntry.name);
			}
			for (const salesOrder of salesOrders.reverse()) {
				await api.cancel("Sales Order", salesOrder.name);
				await api.delete("Sales Order", salesOrder.name);
			}
		}
	});
});

async function createSalesOrder(api: FrappeApi, rate: number, index: number): Promise<SalesOrder> {
	const transactionDate = SALES_WHT_PROCESS.transactionDate;
	return api.createFromFactory<SalesOrder>(
		"Sales Order",
		{
			customer: SALES_WHT_PROCESS.customer,
			transaction_date: transactionDate,
			delivery_date: transactionDate,
			po_no: `Playwright sales withholding tax guide ${index + 1}`,
			items: [{ item_code: SALES_WHT_PROCESS.item, qty: 1, rate }],
		},
		true,
	);
}

async function createDraftPaymentEntry(
	api: FrappeApi,
	firstOrder: SalesOrder,
	secondOrder: SalesOrder,
): Promise<PaymentEntry> {
	const paymentEntry = await api.call<PaymentEntry>(
		"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
		{ dt: "Sales Order", dn: firstOrder.name },
	);
	const total = firstOrder.grand_total + secondOrder.grand_total;
	const secondReference = {
		doctype: "Payment Entry Reference",
		reference_doctype: "Sales Order",
		reference_name: secondOrder.name,
		total_amount: secondOrder.grand_total,
		outstanding_amount: secondOrder.grand_total,
		allocated_amount: secondOrder.grand_total,
		exchange_rate: 1,
	};

	paymentEntry.deductions = [];
	paymentEntry.posting_date = SALES_WHT_PROCESS.transactionDate;
	paymentEntry.references = [paymentEntry.references[0], secondReference];
	paymentEntry.paid_amount = total;
	paymentEntry.received_amount = total;
	paymentEntry.base_paid_amount = total;
	paymentEntry.base_received_amount = total;
	paymentEntry.total_allocated_amount = total;
	paymentEntry.base_total_allocated_amount = total;
	paymentEntry.difference_amount = 0;

	return api.createFromFactory<PaymentEntry>("Payment Entry", paymentEntry);
}

async function getPaymentEntrySummary(page: Page): Promise<PaymentEntrySummary> {
	return page.evaluate(() => {
		const currentForm = (
			window as unknown as {
				cur_frm: {
					doc: {
						deductions: PaymentEntrySummary["deductions"];
						paid_amount: number;
						references: PaymentEntrySummary["references"];
					};
				};
			}
		).cur_frm;
		return {
			deductions: currentForm.doc.deductions || [],
			paidAmount: currentForm.doc.paid_amount,
			references: currentForm.doc.references || [],
		};
	});
}

async function showPaymentTables(
	page: Page,
	references: ReturnType<import("../../pages/form.page").FormPage["field"]>,
	deductions: ReturnType<import("../../pages/form.page").FormPage["field"]>,
) {
	await page.addStyleTag({
		content: `
			[data-fieldname="taxes_and_charges_section"],
			[data-fieldname="purchase_taxes_and_charges_template"],
			[data-fieldname="sales_taxes_and_charges_template"],
			[data-fieldname="taxes"],
			[data-fieldname="base_total_taxes_and_charges"],
			[data-fieldname="total_taxes_and_charges"],
			[data-fieldname="paid_amount_after_tax"],
			[data-fieldname="base_paid_amount_after_tax"],
			[data-fieldname="received_amount_after_tax"],
			[data-fieldname="base_received_amount_after_tax"] {
				display: none !important;
			}
		`,
	});
	await deductions.scrollIntoViewIfNeeded();
	await expect(references).toBeVisible();
	await alignSectionBelowPageHeader(page, "section_break_14");
}

async function alignSectionBelowPageHeader(page: Page, fieldname: string): Promise<void> {
	const section = page.locator(`[data-fieldname="${fieldname}"]`).first();
	await expect(section).toBeVisible();

	await section.evaluate((element) => {
		const scrollContainer = element.closest<HTMLElement>(".main-section");
		const pageHeader = element
			.closest<HTMLElement>(".page-container")
			?.querySelector<HTMLElement>(".page-head");
		if (!scrollContainer || !pageHeader) {
			throw new Error("Payment Entry scroll container or page header was not found");
		}

		// Allow short forms to scroll far enough to place the section below the sticky header.
		scrollContainer.style.paddingBottom = `${window.innerHeight}px`;
		const headerBottom = pageHeader.getBoundingClientRect().bottom;
		scrollContainer.scrollTop += element.getBoundingClientRect().top - headerBottom;
	});

	await expect
		.poll(() =>
			section.evaluate((element) => {
				const pageHeader = element
					.closest<HTMLElement>(".page-container")
					?.querySelector<HTMLElement>(".page-head");
				if (!pageHeader) {
					throw new Error("Payment Entry page header was not found");
				}
				return Math.round(
					element.getBoundingClientRect().top - pageHeader.getBoundingClientRect().bottom,
				);
			}),
		)
		.toBeCloseTo(0);
}
