export const THAI_WHT_SETUP = {
	company: {
		name: "Dunder Mifflin",
		category: "Juristic Person - Domestic",
		salesAccount: "Sales Withholding Tax Receivable - DM",
		purchasePnd3Account: "Purchase Withholding Tax PND 3 Payable - DM",
		purchasePnd53Account: "Purchase Withholding Tax PND 53 Payable - DM",
	},
	category: "Juristic Person - Domestic",
	incomeType: {
		name: "6 เงินได้จากวิชาชีพอิสระ",
		defaultRate: "3",
		pndMappings: [
			["Individual - Domestic", "PND 3"],
			["Juristic Person - Domestic", "PND 53"],
		],
	},
	accounts: [
		"Sales Withholding Tax Receivable - DM",
		"Purchase Withholding Tax PND 3 Payable - DM",
		"Purchase Withholding Tax PND 53 Payable - DM",
	],
	customer: {
		name: "Lackawanna County",
		category: "Juristic Person - Domestic",
	},
	supplier: {
		name: "Hammermill Paper Company",
		category: "Juristic Person - Domestic",
	},
	item: {
		name: "AUDIT-FEE",
		incomeType: "6 เงินได้จากวิชาชีพอิสระ",
	},
	revenueDepartment: "Revenue Department",
} as const;
