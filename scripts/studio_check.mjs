#!/usr/bin/env node
// Contrôle des écrans d'un tournage (skill studio-de-tournage) : rejoue le scénario dans le studio, sans filmer, et lit
// tout le texte visible à l'ouverture, à chaque repère « mark », après chaque geste (clic, survol, touche, saisie) et à
// la fin : un panneau ouvert par un clic est relu, pas seulement l'écran d'avant. Le tournage n'a lieu que si aucun
// écran ne montre d'erreur, de réglage manquant, d'état vide, de chargement sans fin, de ligne répétée ni de fenêtre ou
// de panneau qui sort de l'écran.
//
//   node scripts/studio_check.mjs <scenario.json> <dossier-de-sortie>
//
// Sorties : check.json (constats par écran) et une capture par écran fautif. Code 1 au premier écran bloquant :
// on corrige le studio (données, réglage, semis), jamais le scénario pour cacher un manque.
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { studioChromeOptions, studioCache, studioClock } from "./studio_chrome.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(ROOT, "tools/studio/package.json"));
const { chromium } = require("playwright");
function fail(message) { console.error("studio_check : " + message); process.exit(1); }
const [scenarioPath, outArg] = process.argv.slice(2);
if (!scenarioPath || !outArg || !existsSync(scenarioPath)) fail("usage : node scripts/studio_check.mjs <scenario.json> <dossier-de-sortie>");
const scenario = JSON.parse(readFileSync(scenarioPath, "utf8"));
const out = resolve(outArg);
mkdirSync(out, { recursive: true });

// Ce qu'un écran filmé ne montre jamais. Chaque règle a son exemple vu dans un studio.
const BLOCKING = [
  [/n[’']est pas configuré|n[’']est pas connecté|doit (?:ajouter|activer|créer)|jeton|HUBSPOT_ACCESS_TOKEN|clé .*(?:API|Google)/i, "réglage ou accès manquant (ex. « HubSpot n'est pas configuré sur le serveur »)"],
  [/\b(?:erreur|indisponible|introuvable|impossible|refusé|échec)\b|Réessayer|Traitement indisponible|Consultez le diagnostic/i, "erreur affichée (ex. « Fiche non lue : Traitement indisponible »)"],
  // « Aucune liste » reste permis : c'est le choix par défaut d'un menu (Relier à HubSpot), pas un état vide.
  [/\bAucun(?:e)? (?:secteur|prospect|lead|document|rendez-vous|tournée|résultat|donnée|recherche|contact|élément|entreprise|tableur)|pour le moment|n[’']existent pas encore|pas encore (?:été|de )|Zone non trouvée/i, "donnée manquante (ex. « Aucun secteur n'est prévu en novembre », « Aucune recherche pour le moment »)"],
  [/\b(?:À|A) valider\b|\b(?:À|A) rechercher\b/i, "valeur non résolue"],
  [/\bundefined\b|\bNaN\b|\[object Object\]/, "valeur non résolue (code)"],
];
const LOADING = /Chargement|Calcul(?:…|\.\.\.)|Recherche(?:…|\.\.\.)|Recherche en cours|(?:Recherche|Calcul) en attente|en file d['’]attente/i;
const ADVISORY = [[/\bNon (?:trouvé|mesurée?|publié|confirmé)\b/i, "valeur finale « Non trouvé » : préférer une entreprise mieux renseignée pour un gros plan"]];

const browser = await chromium.launch(studioChromeOptions(scenario));
const context = await browser.newContext({ viewport: scenario.viewport ?? { width: 1920, height: 1080 }, locale: scenario.locale ?? "fr-FR",
  timezoneId: scenario.timezone ?? "Europe/Paris", colorScheme: scenario.theme === "dark" ? "dark" : "light", extraHTTPHeaders: scenario.headers ?? {} });
await studioCache(context, scenario);
await studioClock(context, scenario);
const page = await context.newPage();
const target = (t, where = page) => {
  let loc;
  if (t.role) loc = where.getByRole(t.role, t.name ? { name: t.name, exact: t.exact ?? false } : {});
  else if (t.label) loc = where.getByLabel(t.label, { exact: t.exact ?? false });
  else if (t.placeholder) loc = where.getByPlaceholder(t.placeholder, { exact: t.exact ?? false });
  else if (t.testId) loc = where.getByTestId(t.testId);
  else if (t.text) loc = where.getByText(t.text, { exact: t.exact ?? false });
  else loc = where.locator(t.selector);
  if (t.within) loc = target(t.within, where).locator(loc);
  return t.nth !== undefined ? loc.nth(t.nth) : loc.first();
};
const screens = [];
async function at(t) {
  if (!t.at) return undefined;
  const box = await target(t).boundingBox();
  if (!box) throw new Error("Cible sans position : " + JSON.stringify(t));
  return { x: box.width * (t.at.x ?? 0.5), y: box.height * (t.at.y ?? 0.5) };
}
async function inspect(label) {
  // Un chargement a 20 s pour finir avant d'être compté comme un manque.
  let text = "";
  for (let k = 0; k < 20; k++) {
    text = await page.evaluate(() => document.body.innerText);
    if (!LOADING.test(text)) break;
    await page.waitForTimeout(1000);
  }
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const found = [];
  for (const line of lines) {
    for (const [re, why] of BLOCKING) if (re.test(line)) found.push({ level: "bloquant", why, text: line.slice(0, 220) });
    if (LOADING.test(line)) found.push({ level: "bloquant", why: "chargement qui ne finit pas en 20 s", text: line.slice(0, 220) });
    for (const [re, why] of ADVISORY) if (re.test(line)) found.push({ level: "conseil", why, text: line.slice(0, 220) });
  }
  for (const entry of await page.locator('[role="alert"]:visible').allInnerTexts()) {
    const value = entry.trim();
    if (value && !found.some((finding) => finding.text === value.slice(0, 220))) {
      found.push({ level: "bloquant", why: "alerte affichée", text: value.slice(0, 220) });
    }
  }
  // Même ligne trois fois de suite (ex. six sources « Responsable technique · Julien Roux ») : doublon de données.
  // Un agenda peut répéter le texte du bouton dans des cellules différentes, chacune nommant son jour et son plan.
  const tableActions = await page.locator('td button[aria-label]').evaluateAll((buttons) =>
    buttons.map((button) => [button.innerText.trim(), button.getAttribute('aria-label')]));
  for (let k = 0; k + 2 < lines.length; k++) {
    if (lines[k].length > 3 && lines[k] === lines[k + 1] && lines[k] === lines[k + 2]) {
      let n = 3; while (lines[k + n] === lines[k]) n++;
      const labels = new Set(tableActions.filter(([text]) => text === lines[k]).map(([, label]) => label));
      if (labels.size !== lines.filter((line) => line === lines[k]).length) {
        found.push({ level: "bloquant", why: "ligne répétée " + n + " fois (doublon de données)", text: lines[k].slice(0, 220) });
      }
      k += n - 1;
    }
  }
  // Fenêtre, fiche ou panneau ouvert qui dépasse de l'écran.
  const overflow = await page.evaluate(() => {
    const W = window.innerWidth, H = window.innerHeight, bad = [];
    for (const el of document.querySelectorAll('[role="dialog"], [aria-modal="true"], [role="alertdialog"], [role="complementary"], [data-state="open"]')) {
      const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
      if (cs.display === "none" || cs.visibility === "hidden" || r.width < 40 || r.height < 40) continue;
      if (cs.position !== "fixed" && cs.position !== "absolute") continue;
      if (r.left < -2 || r.top < -2 || r.right > W + 2 || r.bottom > H + 2) bad.push((el.getAttribute("aria-label") || el.innerText || "").trim().split("\n")[0].slice(0, 80) + " [" + [r.left, r.top, r.right, r.bottom].map(Math.round).join(", ") + "]");
    }
    return bad;
  });
  for (const o of overflow) found.push({ level: "bloquant", why: "panneau ou fenêtre qui dépasse de l'écran", text: o });
  // Image cassée ou emplacement vide (couverture d'un sujet sans image, logo absent) : un manque visible.
  const empty = await page.evaluate(() => {
    const W = window.innerWidth, H = window.innerHeight, bad = [];
    const shown = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      return r.width > 16 && r.height > 16 && r.bottom > 0 && r.right > 0 && r.top < H && r.left < W && cs.visibility !== "hidden" && cs.display !== "none" && +cs.opacity > 0.05; };
    for (const img of document.querySelectorAll("img")) if (img.complete && img.naturalWidth === 0 && img.getAttribute("src") && shown(img)) bad.push("image cassée " + img.getAttribute("src").slice(0, 80));
    for (const el of document.querySelectorAll('[class*="--empty"]')) if (shown(el)) {
      const card = el.closest("article, li, a, button, [class*=card]") || el.parentElement;
      bad.push("emplacement vide (" + [...el.classList].find((c) => c.endsWith("--empty")) + ") : " + ((card && card.innerText) || "").trim().split("\n")[0].slice(0, 80));
    }
    return bad;
  });
  for (const e of empty) found.push({ level: "bloquant", why: "image ou couverture manquante", text: e });
  const blocking = found.filter((f) => f.level === "bloquant");
  const shot = blocking.length ? join(out, "ecran-" + String(screens.length).padStart(2, "0") + "-" + label.replace(/[^a-z0-9-]+/gi, "_") + ".png") : null;
  if (shot) await page.screenshot({ path: shot, fullPage: true });
  screens.push({ label, url: page.url(), found, shot });
  console.log((blocking.length ? "BLOQUANT " : "ok       ") + label + (blocking.length ? " : " + blocking.map((f) => "« " + f.text + " »").join(" ; ") : ""));
}

await page.goto(scenario.url, { waitUntil: "networkidle", timeout: 120000 });
if (scenario.waitFor) await target(scenario.waitFor).waitFor({ state: "visible", timeout: 60000 });
await page.waitForTimeout(scenario.settleMs ?? 600);
await inspect("ouverture");
// Une commande du studio pendant le parcours (la réponse d'un collègue, par exemple), puis l'événement que la page
// écoute pour relire ses données. Elle échoue bruyamment : son code de sortie arrête le contrôle.
async function runStep(step) {
  if (!Array.isArray(step.cmd) || !step.cmd.length) throw new Error("étape run sans commande (cmd : [programme, arguments…])");
  const done = spawnSync(step.cmd[0], step.cmd.slice(1), { cwd: step.cwd ? resolve(step.cwd) : process.cwd(), encoding: "utf8", timeout: (step.timeout ?? 60) * 1000 });
  if (done.status !== 0) throw new Error("commande " + step.cmd.join(" ") + " : code " + done.status + " " + String(done.stderr || done.error || "").trim().slice(0, 300));
  if (step.dispatch) await page.evaluate((name) => window.dispatchEvent(new Event(name)), step.dispatch);
}
for (const [i, step] of (scenario.steps ?? []).entries()) {
  try {
    switch (step.action) {
      case "mark": await inspect(step.label); break;
      case "pause": await page.waitForTimeout(step.ms ?? 1000); break;
      case "click": await target(step.target).click({ timeout: step.target.timeout ?? 15000, position: await at(step.target), ...(step.button ? { button: step.button } : {}) }); break;
      case "hover": await target(step.target).hover({ timeout: 15000, position: await at(step.target) }); break;
      case "drag": {
        if (!step.by) { await target(step.target).dragTo(target(step.destination), { timeout: 15000 }); break; }
        // Glisser d'un décalage en pixels CSS (un angle de la délimitation du parking).
        const b = await target(step.target).boundingBox({ timeout: 15000 });
        if (!b) throw new Error("élément à glisser sans position : " + JSON.stringify(step.target));
        const x = b.x + b.width / 2, y = b.y + b.height / 2;
        await page.mouse.move(x, y); await page.mouse.down();
        await page.mouse.move(x + step.by.x, y + step.by.y, { steps: 12 }); await page.mouse.up();
        break;
      }
      case "run": await runStep(step); break;
      case "fill": await target(step.target).fill(step.value, { timeout: 15000 }); break;
      case "type": if (step.target) await target(step.target).click(); await page.keyboard.type(step.text, { delay: 20 }); break;
      case "press": await page.keyboard.press(step.key); break;
      case "select": await target(step.target).selectOption(step.value); break;
      case "scroll": if (step.target) await target(step.target).hover({ timeout: 15000 }); await page.mouse.wheel(0, step.y ?? 600); break;
      case "wait": step.target ? await target(step.target).waitFor({ state: "visible", timeout: step.timeout ?? 30000 }) : await page.waitForTimeout(step.ms ?? 1000); break;
      case "goto": await page.goto(new URL(step.url, page.url()).href, { waitUntil: "networkidle" }); break;
      case "screenshot": break;
      case "expect": {
        // Valeur attendue à l'écran (ex. la case Prospects de Bigup montre toujours 25 prospects).
        const got = ((await target(step.target).textContent({ timeout: 15000 }).catch(() => "")) || "").trim();
        const ok = step.text !== undefined ? got === String(step.text) : got.length > 0;
        const entry = { label: "attendu " + JSON.stringify(step.target), found: ok ? [] : [{ level: "bloquant", why: "valeur attendue « " + step.text + " »", text: "lu « " + got + " »" }] };
        screens.push(entry);
        console.log((ok ? "ok       " : "BLOQUANT ") + "attendu « " + step.text + " » : lu « " + got + " »");
        break;
      }
      default: fail("étape " + i + " : geste inconnu « " + step.action + " ».");
    }
  } catch (e) { screens.push({ label: "étape " + i, found: [{ level: "bloquant", why: "geste impossible", text: String(e.message).split("\n")[0] }] }); console.log("BLOQUANT étape " + i + " (" + step.action + ") : " + String(e.message).split("\n")[0]); break; }
  if (!["pause", "mark", "screenshot", "expect"].includes(step.action)) {
    await page.waitForTimeout(step.delay ?? 650);
    // Ce que le geste a ouvert est filmé : le relire aussi.
    if (step.action !== "wait") await inspect("après " + step.action + " " + JSON.stringify(step.target ?? step.key ?? step.url ?? "").slice(0, 60));
  }
}
await inspect("fin");
await browser.close();
const blocking = screens.flatMap((s) => s.found.filter((f) => f.level === "bloquant").map((f) => ({ ...f, screen: s.label })));
const sha = createHash("sha256").update(readFileSync(scenarioPath)).digest("hex");
writeFileSync(join(out, "check.json"), JSON.stringify({ scenario: resolve(scenarioPath), scenario_sha256: sha, at: new Date().toISOString(), screens, blocking: blocking.length }, null, 2));
if (blocking.length) fail(blocking.length + " constat(s) bloquant(s) : corriger le studio (semis, réglages, données) puis relancer. Détail : " + join(out, "check.json"));
console.log("studio_check : " + screens.length + " écrans relus, aucun manque de donnée ni erreur.");

