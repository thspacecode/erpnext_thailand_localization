import type { Page } from "@playwright/test";

import type { FrappeApi, FrappeDocument } from "../../fixtures/frappe-api";
import { expect, test } from "../../fixtures/test";
import { formatDeskDate } from "../../pages/desk.page";

const PURCHASE_WHT_PROCESS = {
	supplier: "Hammermill Paper Company",
	item: "AUDIT-FEE",
	incomeType: "6 เงินได้จากวิชาชีพอิสระ",
	payableAccount: "Purchase Withholding Tax PND 53 Payable - DM",
	transactionDate: `${new Date().getUTCFullYear()}-01-15`,
	orderRates: [5_000, 8_000, 5_000],
} as const;

type PurchaseOrder = FrappeDocument & {
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
	formatDeskDate(PURCHASE_WHT_PROCESS.transactionDate),
	"15-01-20XX",
];

test.describe("Purchase withholding tax process", () => {
	test("Creates withholding-tax deductions from purchase orders", async ({
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

		const purchaseOrders: PurchaseOrder[] = [];
		let draftPaymentEntry: PaymentEntry | undefined;

		try {
			for (const [index, rate] of PURCHASE_WHT_PROCESS.orderRates.entries()) {
				purchaseOrders.push(await createPurchaseOrder(api, rate, index));
			}

			await test.step("Option A: open Payment Entry from a submitted Purchase Order", async () => {
				const purchaseOrder = purchaseOrders[0];
				await page.setViewportSize({ width: 1440, height: 900 });
				await desk.goToDoc("Purchase Order", purchaseOrder.name);
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
					[purchaseOrder.name, "PUR-ORD-YYYY-00001"],
					transactionDateReplacement,
				]);
				await expectScreenshot("purchase-order-create-payment-entry.png");

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
						reference_doctype: "Purchase Order",
						reference_name: purchaseOrder.name,
					}),
				]);
				expect(summary.deductions).toEqual([
					expect.objectContaining({
						account: PURCHASE_WHT_PROCESS.payableAccount,
						amount: -150,
						custom_base_amount: 5_000,
						custom_income_type: PURCHASE_WHT_PROCESS.incomeType,
						custom_reference_document: purchaseOrder.name,
						custom_reference_document_type: "Purchase Order",
						custom_tax_rate: 3,
					}),
				]);

				await showPaymentTables(page, form.field("references"), form.field("deductions"));
				await desk.normalizeDocumentNames([
					[purchaseOrder.name, "PUR-ORD-YYYY-00001"],
					transactionDateReplacement,
				]);
				await expectScreenshot("payment-entry-from-purchase-order.png");
			});

			await test.step("Option B: get withholding tax from two Purchase Order references", async () => {
				draftPaymentEntry = await createDraftPaymentEntry(
					api,
					purchaseOrders[1],
					purchaseOrders[2],
				);
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
					[purchaseOrders[1].name, "PUR-ORD-YYYY-00002"],
					[purchaseOrders[2].name, "PUR-ORD-YYYY-00003"],
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
						amount: -240,
						custom_base_amount: 8_000,
						custom_reference_document: purchaseOrders[1].name,
					}),
					expect.objectContaining({
						amount: -150,
						custom_base_amount: 5_000,
						custom_reference_document: purchaseOrders[2].name,
					}),
				]);

				await expect(page.locator(".alert-message")).toBeHidden({ timeout: 15_000 });
				await showPaymentTables(page, form.field("references"), form.field("deductions"));
				await desk.normalizeDocumentNames([
					[purchaseOrders[1].name, "PUR-ORD-YYYY-00002"],
					[purchaseOrders[2].name, "PUR-ORD-YYYY-00003"],
					transactionDateReplacement,
				]);
				await expectScreenshot("payment-entry-withholding-tax-from-references.png");
			});
		} finally {
			if (draftPaymentEntry) {
				await api.delete("Payment Entry", draftPaymentEntry.name);
			}
			for (const purchaseOrder of purchaseOrders.reverse()) {
				await api.cancel("Purchase Order", purchaseOrder.name);
				await api.delete("Purchase Order", purchaseOrder.name);
			}
		}
	});
});

async function createPurchaseOrder(
	api: FrappeApi,
	rate: number,
	index: number,
): Promise<PurchaseOrder> {
	const transactionDate = PURCHASE_WHT_PROCESS.transactionDate;
	return api.createFromFactory<PurchaseOrder>(
		"Purchase Order",
		{
			supplier: PURCHASE_WHT_PROCESS.supplier,
			transaction_date: transactionDate,
			schedule_date: transactionDate,
			remarks: `Playwright purchase withholding tax guide ${index + 1}`,
			items: [{ item_code: PURCHASE_WHT_PROCESS.item, qty: 1, rate }],
		},
		true,
	);
}

async function createDraftPaymentEntry(
	api: FrappeApi,
	firstOrder: PurchaseOrder,
	secondOrder: PurchaseOrder,
): Promise<PaymentEntry> {
	const paymentEntry = await api.call<PaymentEntry>(
		"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
		{ dt: "Purchase Order", dn: firstOrder.name },
	);
	const total = firstOrder.grand_total + secondOrder.grand_total;
	const secondReference = {
		doctype: "Payment Entry Reference",
		reference_doctype: "Purchase Order",
		reference_name: secondOrder.name,
		total_amount: secondOrder.grand_total,
		outstanding_amount: secondOrder.grand_total,
		allocated_amount: secondOrder.grand_total,
		exchange_rate: 1,
	};

	paymentEntry.deductions = [];
	paymentEntry.posting_date = PURCHASE_WHT_PROCESS.transactionDate;
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
		.toBe(0);
}
