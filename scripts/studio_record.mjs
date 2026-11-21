#!/usr/bin/env node
// Studio de tournage : filmer un parcours d'interface en 4K avec Playwright (skill studio-de-tournage).
//
//   node scripts/studio_record.mjs <scenario.json> <dossier-de-sortie>
//
// Le scénario décrit la page de départ et les gestes (click, type, press, hover, scroll, select, wait, pause,
// goto, mark). Le navigateur est piloté par une vraie souris et un vrai clavier (Playwright), filmé par le flux
// d'images de Chrome à la densité 2 (1920 x 1080 CSS -> 3840 x 2160), sans curseur : le curseur, les clics et
// les zooms sont dessinés au montage (kit tuto-interface) d'après le journal.
// Sorties : raw.mp4 (60 i/s constants), timeline.json (format TimelineData : fps, width, height, zoom,
// frames[].cursor en pixels CSS, events[] click|key, markers[] pour caler la voix), shots/ (captures demandées).
import { createRequire } from "node:module";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(ROOT, "tools/studio/package.json"));
let chromium;
try { ({ chromium } = require("playwright")); }
catch { fail("Playwright absent : lancez « cd tools/studio && npm ci » puis « npx playwright install chromium »."); }

function fail(message) { console.error("studio_record : " + message); process.exit(1); }
const [scenarioPath, outArg] = process.argv.slice(2);
if (!scenarioPath || !outArg) fail("usage : node scripts/studio_record.mjs <scenario.json> <dossier-de-sortie>");
if (!existsSync(scenarioPath)) fail("scénario introuvable : " + scenarioPath);
const scenario = JSON.parse(readFileSync(scenarioPath, "utf8"));
const out = resolve(outArg);
const framesDir = join(out, "frames");
mkdirSync(framesDir, { recursive: true });
mkdirSync(join(out, "shots"), { recursive: true });

const FPS = 60;
const view = { width: scenario.viewport?.width ?? 1920, height: scenario.viewport?.height ?? 1080 };
const density = scenario.density ?? 2;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: view, deviceScaleFactor: density, locale: scenario.locale ?? "fr-FR",
  timezoneId: scenario.timezone ?? "Europe/Paris", colorScheme: scenario.theme === "dark" ? "dark" : "light",
  extraHTTPHeaders: scenario.headers ?? {},
});
const page = await context.newPage();
const target = (t, where = page) => {
  if (!t || typeof t !== "object") fail("cible manquante ou invalide : " + JSON.stringify(t));
  let loc;
  if (t.role) loc = where.getByRole(t.role, t.name ? { name: t.name, exact: t.exact ?? false } : {});
  else if (t.label) loc = where.getByLabel(t.label, { exact: t.exact ?? false });
  else if (t.placeholder) loc = where.getByPlaceholder(t.placeholder, { exact: t.exact ?? false });
  else if (t.testId) loc = where.getByTestId(t.testId);
  else if (t.text) loc = where.getByText(t.text, { exact: t.exact ?? false });
  else if (t.selector) loc = where.locator(t.selector);
  else fail("cible sans role, label, placeholder, testId, text ni selector : " + JSON.stringify(t));
  if (t.within) loc = target(t.within, where).locator(loc);
  return t.nth !== undefined ? loc.nth(t.nth) : loc.first();
};

try {
  await page.goto(scenario.url, { waitUntil: "networkidle", timeout: 60000 });
} catch (e) { fail("la page de départ ne s'ouvre pas (" + scenario.url + ") : " + e.message.split("\n")[0]); }
if (scenario.waitFor) await target(scenario.waitFor).waitFor({ state: "visible", timeout: 30000 });
if (scenario.hideScrollbars !== false) await page.addStyleTag({ content: "::-webkit-scrollbar{display:none!important}*{scrollbar-width:none!important}" });
await sleep(scenario.settleMs ?? 600);

// Le film : chaque image du flux de Chrome est gardée avec son heure ; l'assemblage la tient jusqu'à la suivante.
const cdp = await context.newCDPSession(page);
const frames = [];
cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
  const file = join(framesDir, String(frames.length).padStart(6, "0") + ".jpg");
  writeFileSync(file, Buffer.from(data, "base64"));
  frames.push({ file, t: metadata.timestamp });
  try { await cdp.send("Page.screencastFrameAck", { sessionId }); } catch {}
});
await cdp.send("Page.startScreencast", { format: "jpeg", quality: scenario.jpegQuality ?? 94, maxWidth: view.width * density, maxHeight: view.height * density, everyNthFrame: 1 });
// Une première image certaine, même si rien ne bouge.
await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
await sleep(300);
const t0 = frames.length ? frames[0].t : now();

const cursor = { x: scenario.cursorStart?.x ?? view.width * 0.62, y: scenario.cursorStart?.y ?? view.height * 0.7 };
const samples = [{ t: now(), x: cursor.x, y: cursor.y, down: false }];
const events = [], markers = [];
const log = (down = false) => samples.push({ t: now(), x: cursor.x, y: cursor.y, down });
const ease = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);

async function moveTo(x, y) {
  const dx = x - cursor.x, dy = y - cursor.y, dist = Math.hypot(dx, dy);
  if (dist < 1) return;
  const ms = Math.min(1000, Math.max(380, 300 + dist * 0.45));
  const sx = cursor.x, sy = cursor.y, start = Date.now();
  // Légère courbe, comme une main : le point de contrôle s'écarte de la ligne droite.
  const bend = Math.min(60, dist * 0.08) * (dx > 0 ? 1 : -1);
  for (;;) {
    const u = Math.min(1, (Date.now() - start) / ms), e = ease(u), arc = Math.sin(Math.PI * u) * bend;
    cursor.x = sx + dx * e - (dy / (dist || 1)) * arc;
    cursor.y = sy + dy * e + (dx / (dist || 1)) * arc;
    await page.mouse.move(cursor.x, cursor.y);
    log();
    if (u >= 1) break;
    await sleep(14);
  }
}
async function pointAt(t) {
  const loc = target(t);
  try { await loc.waitFor({ state: "visible", timeout: t.timeout ?? 15000 }); }
  catch { fail("élément introuvable ou invisible : " + JSON.stringify(t)); }
  await loc.scrollIntoViewIfNeeded();
  const box = await loc.boundingBox();
  if (!box) fail("élément sans position à l'écran : " + JSON.stringify(t));
  const x = box.x + box.width * (t.at?.x ?? 0.5), y = box.y + box.height * (t.at?.y ?? 0.5);
  await moveTo(x, y);
  return loc;
}
async function click(t) {
  await pointAt(t);
  await sleep(140);
  log(true); await page.mouse.down(); await sleep(70); await page.mouse.up(); log(false);
  events.push({ type: "click", timeMs: (now() - t0) * 1000 });
}

const DEFAULT_DELAY = scenario.defaultDelay ?? 650;
for (const [i, step] of (scenario.steps ?? []).entries()) {
  const where = "étape " + i + " (" + step.action + ")";
  try {
    switch (step.action) {
      case "pause": await sleep(step.ms ?? 1000); log(); break;
      case "mark": markers.push({ label: step.label, timeMs: (now() - t0) * 1000 }); break;
      case "click": await click(step.target); break;
      case "hover": await pointAt(step.target); break;
      case "type": {
        if (step.target) await click(step.target);
        for (const ch of step.text) {
          await page.keyboard.type(ch);
          events.push({ type: "key", timeMs: (now() - t0) * 1000 });
          await sleep(step.charDelay ?? 55);
        }
        break;
      }
      case "press": await page.keyboard.press(step.key); events.push({ type: "key", timeMs: (now() - t0) * 1000 }); break;
      case "select": { const loc = await pointAt(step.target); await loc.selectOption(step.value); events.push({ type: "click", timeMs: (now() - t0) * 1000 }); break; }
      case "scroll": {
        if (step.target) await pointAt(step.target);
        const total = step.y ?? 600, n = Math.max(12, Math.round(Math.abs(total) / 25));
        for (let k = 0; k < n; k++) { await page.mouse.wheel(0, total / n); await sleep(16); }
        log(); break;
      }
      case "wait": step.target ? await target(step.target).waitFor({ state: "visible", timeout: step.timeout ?? 30000 }) : await sleep(step.ms ?? 1000); break;
      case "goto": await page.goto(new URL(step.url, page.url()).href, { waitUntil: "networkidle" }); break;
      case "screenshot": await page.screenshot({ path: join(out, "shots", step.name + ".png") }); break;
      default: fail(where + " : geste inconnu. Gestes : click, type, press, hover, scroll, select, wait, pause, goto, mark, screenshot.");
    }
  } catch (e) { fail(where + " : " + String(e.message || e).split("\n")[0]); }
  if (!["pause", "mark", "screenshot"].includes(step.action)) await sleep(step.delay ?? DEFAULT_DELAY);
}
await sleep(scenario.tailMs ?? 900); log();
const tEnd = now();
await cdp.send("Page.stopScreencast");
await sleep(200);
await browser.close();
if (frames.length < 2) fail("aucune image filmée : la page n'a rien affiché (vérifiez l'adresse du studio).");

// Assemblage à 60 i/s constants : chaque image dure jusqu'à la suivante.
const list = frames.map((f, k) => "file '" + f.file.replace(/'/g, "'\\''") + "'\nduration " + Math.max(0.001, ((frames[k + 1]?.t ?? tEnd) - f.t)).toFixed(4)).join("\n") + "\nfile '" + frames.at(-1).file + "'\n";
writeFileSync(join(out, "frames.txt"), list);
const W = view.width * density, H = view.height * density;
const ff = spawnSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", join(out, "frames.txt"),
  "-vf", "fps=" + FPS + ",scale=" + W + ":" + H + ":flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
  "-t", ((Math.round((tEnd - t0) * FPS)) / FPS).toFixed(4), "-movflags", "+faststart", join(out, "raw.mp4")], { stdio: "inherit" });
if (ff.status !== 0) fail("l'assemblage ffmpeg a échoué (code " + ff.status + ").");

// Journal au format TimelineData : position du curseur à chaque image, en pixels CSS.
const count = Math.round((tEnd - t0) * FPS);
const timeline = { fps: FPS, width: W, height: H, zoom: density, frames: [], events, markers,
  capture: { source_frames: frames.length, seconds: +(tEnd - t0).toFixed(3), source_fps: +(frames.length / (tEnd - t0)).toFixed(1) } };
let j = 0;
for (let n = 0; n < count; n++) {
  const t = t0 + n / FPS;
  while (j + 1 < samples.length && samples[j + 1].t <= t) j++;
  const a = samples[j], b = samples[j + 1];
  const u = b && b.t > a.t ? Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t))) : 0;
  const x = b ? a.x + (b.x - a.x) * u : a.x, y = b ? a.y + (b.y - a.y) * u : a.y;
  timeline.frames.push({ cursor: { x: +x.toFixed(1), y: +y.toFixed(1), scale: a.down ? 0.82 : 1 }, hud: null });
}
writeFileSync(join(out, "timeline.json"), JSON.stringify(timeline));
console.log("studio_record : " + count + " images (" + timeline.capture.seconds + " s, " + timeline.capture.source_fps + " images/s filmées), " + events.length + " gestes -> " + join(out, "raw.mp4"));

