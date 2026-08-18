import fs from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";

const sarabunFont = fs.readFileSync(
	path.resolve(__dirname, "../fonts/Sarabun-Regular.ttf"),
	"base64",
);

export class BasePage {
	constructor(readonly page: Page) {}

	async installFonts() {
		await this.page.addInitScript((fontData) => {
			const style = document.createElement("style");
			style.textContent = `
				@font-face {
					font-family: "Sarabun";
					src: url("data:font/ttf;base64,${fontData}") format("truetype");
					font-style: normal;
					font-weight: 400;
				}
				:root {
					--font-stack: InterVariable, "Sarabun", sans-serif;
				}
			`;
			document.addEventListener(
				"DOMContentLoaded",
				() => document.head.appendChild(style),
				{ once: true },
			);
		}, sarabunFont);
	}
}
