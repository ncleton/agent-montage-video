#!/usr/bin/env node
// Ouvre l'accueil du commercial de démonstration comme lui, laisse Bigup noter ses prospects (calcul du navigateur,
// comme en production) et écrit le rapport de notes envoyé à la plateforme, s'il y en a un.
//   node seed/open_home.mjs <sortie.json>
import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const require = createRequire(fileURLToPath(new URL("../../../tools/studio/package.json", import.meta.url)));
const { chromium } = require("playwright");
const out = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
let report = null;
page.on("request", (r) => { if (r.url().includes("shared-book-act") && (r.postData() || "").includes("sync_book_rows")) report = JSON.parse(r.postData()).args.data; });
await page.goto("http://127.0.0.1:55813/", { waitUntil: "networkidle", timeout: 120000 });
await page.getByRole("heading", { name: /Prospects/ }).waitFor({ timeout: 60000 });
await page.waitForTimeout(15000);
// Bigup note le livret à l'ouverture d'une fiche : on ouvre la première, comme le commercial.
await page.locator(".hj-prospects li, .hj-prospects [role=button], .hj-prospects a").first().click({ timeout: 20000 }).catch(() => {});
for (let i = 0; i < 40 && !report; i++) await page.waitForTimeout(1000);
await page.goto("http://127.0.0.1:55813/", { waitUntil: "networkidle", timeout: 120000 });
await page.getByRole("heading", { name: /Prospects/ }).waitFor({ timeout: 60000 });
// L'accueil montre d'abord la dernière lecture gardée, puis la rafraîchit : on attend un compte stable.
const expected = process.argv[3] || null;
let shown = null, same = 0;
for (let i = 0; i < 60 && same < 8; i++) {
  await page.waitForTimeout(1000);
  const now = (await page.locator(".hj-prospects .hj-count").first().textContent().catch(() => null))?.trim() ?? null;
  same = now && now === shown && (!expected || now === expected) ? same + 1 : 0;
  shown = now;
}
writeFileSync(out, JSON.stringify({ report, shown }));
console.log("Prospects affichés : " + shown + (report ? " ; notes envoyées pour " + report.rows.length + " entreprises" : " ; notes inchangées"));
await browser.close();

