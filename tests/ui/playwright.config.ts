import { defineConfig, devices } from "@playwright/test";
import * as dotenv from "dotenv";
import path from "node:path";

dotenv.config({ path: path.resolve(__dirname, ".env") });

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:8000";

// The setup project writes the authenticated Frappe session here for reuse.
export const STORAGE_STATE = path.resolve(__dirname, "playwright/.auth/user.json");

export default defineConfig({
	testDir: ".",
	timeout: 60_000,
	expect: { timeout: 15_000 },
	fullyParallel: true,
	forbidOnly: Boolean(process.env.CI),
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: process.env.CI
		? [["list"], ["html", { open: "never" }], ["github"]]
		: [["list"], ["html", { open: "never" }]],

	use: {
		baseURL,
		trace: "retain-on-failure",
		screenshot: "only-on-failure",
		video: "retain-on-failure",
		ignoreHTTPSErrors: true,
		actionTimeout: 15_000,
		navigationTimeout: 30_000,
	},

	projects: [
		{
			name: "setup",
			testMatch: /.*\.setup\.ts/,
		},
		{
			name: "chromium",
			use: {
				...devices["Desktop Chrome"],
				storageState: STORAGE_STATE,
			},
			dependencies: ["setup"],
		},
	],

	webServer: {
		command: "bench serve --port 8000",
		cwd: path.resolve(__dirname, "../../../.."),
		url: baseURL,
		timeout: 180_000,
		reuseExistingServer: !process.env.CI,
		stdout: "pipe",
		stderr: "pipe",
	},
});
