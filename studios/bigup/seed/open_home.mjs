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
const opened = await page.locator(".hj-prospects").getByText(/\/ 100/).first().click({ timeout: 20000 }).then(() => true).catch(() => false);
if (!opened) { console.error("aucune fiche de prospect ne s'ouvre depuis l'accueil"); process.exit(1); }
for (let i = 0; i < 40 && !report; i++) await page.waitForTimeout(1000);
await page.goto("http://127.0.0.1:55813/", { waitUntil: "networkidle", timeout: 120000 });
await page.getByRole("heading", { name: /Prospects/ }).waitFor({ timeout: 60000 });
// L'accueil montre d'abord la dernière lecture gardée, puis la rafraîchit : on attend un compte stable.
const expected = process.argv[3] || null;
let shown = null, same = 0;
for (let attempt = 0; attempt < 3 && same < 8; attempt++) {
  if (attempt) {
    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("heading", { name: /Prospects/ }).waitFor({ timeout: 60000 });
  }
  same = 0;
  for (let i = 0; i < 45 && same < 8; i++) {
    await page.waitForTimeout(1000);
    const now = (await page.locator(".hj-prospects .hj-count").first().textContent().catch(() => null))?.trim() ?? null;
    same = now && now === shown && (!expected || now === expected) ? same + 1 : 0;
    shown = now;
  }
}
// Les notes telles que la case Prospects les affiche : identifiant de la fiche et note sur 100.
const rows = await page.$$eval(".hj-prospects li.hj-prospect", (items) => items.map((li) => {
  const href = li.querySelector("a.hj-item-main")?.getAttribute("href") || "";
  return { id: new URLSearchParams(href.split("?")[1] || "").get("fiche"), score: Number(li.querySelector(".hj-score strong")?.textContent || "NaN") };
}));
writeFileSync(out, JSON.stringify({ report, shown, rows }));
console.log("Prospects affichés : " + shown + (report ? " ; notes envoyées pour " + report.rows.length + " entreprises" : " ; notes inchangées"));
await browser.close();

