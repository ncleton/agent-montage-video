#!/usr/bin/env node
// Semis des secteurs de tournée du commercial de démonstration (Tournées › Secteurs), comme il les déclarerait lui-même,
// dans sa zone : « Métropole lilloise » pour le Nord, un second secteur pour ses autres départements. Les semaines suivent
// la date du jour ; un secteur devenu hors zone est archivé.
//   node seed/seed_tours.mjs
import { call } from "./call.mjs";

const NAMES = { "02": "Aisne", "08": "Ardennes", "59": "Nord", "60": "Oise", "62": "Pas-de-Calais", "80": "Somme", "51": "Marne", "76": "Seine-Maritime" };
function isoWeek(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const year = t.getUTCFullYear();
  return year + "-W" + String(Math.ceil(((t - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7)).padStart(2, "0");
}
const week = (offset) => isoWeek(new Date(Date.now() + offset * 7 * 86400000));
const current = await call("commercial", "get_tour_plans", {}, "site");
const zone = (current.zone && current.zone.departments) || [];
if (!zone.length) { console.error("Semis des secteurs : le commercial n'a pas de zone (seed_bigup.py la règle)."); process.exit(1); }
const north = zone.includes("59") ? ["59"] : [zone[0]];
const rest = zone.filter((d) => !north.includes(d)).slice(0, 4);
const PLANS = [{ name: "Métropole lilloise", departments: north, weeks: [week(0), week(1), week(3)], color: 2 }];
if (rest.length) PLANS.push({ name: rest.map((d) => NAMES[d] || d).join(", ").replace(/, ([^,]*)$/, " et $1"), departments: rest, weeks: [week(-1), week(2)], color: 5 });
const wanted = new Set(PLANS.map((p) => p.name));
const existing = new Map((current.plans || []).map((p) => [p.name, p]));
for (const plan of current.plans || []) {
  if (wanted.has(plan.name)) continue;
  await call("commercial", "save_tour_plan", { id: plan.id, expected_revision: plan.revision, idempotency_key: "studio-plan-archive-" + plan.id + "-" + Date.now(), data: { archived: true } }, "site");
  console.log("Archivé : " + plan.name);
}
for (const plan of PLANS) {
  const found = existing.get(plan.name);
  const args = { idempotency_key: "studio-plan-" + plan.name + "-" + Date.now(), data: plan };
  if (found) { args.id = found.id; args.expected_revision = found.revision; }
  const saved = await call("commercial", "save_tour_plan", args, "site");
  console.log((found ? "Mis à jour : " : "Créé : ") + saved.plan.name + " · " + saved.plan.departments.join(", ") + " · " + saved.plan.weeks.map((w) => w.week ?? w.id ?? JSON.stringify(w)).join(", "));
}

