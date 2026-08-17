export const CREDENTIALS = {
	user: process.env.FRAPPE_TEST_USER ?? "Administrator",
	password: process.env.FRAPPE_TEST_PASSWORD ?? "admin",
} as const;
