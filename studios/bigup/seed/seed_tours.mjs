#!/usr/bin/env node
// Semis des secteurs de tournée du commercial de démonstration (Tournées › Secteurs), comme il les déclarerait lui-même.
// Les semaines suivent la date du jour : la semaine en cours, la suivante et les deux d'après.
//   node seed/seed_tours.mjs
import { call } from "./call.mjs";

function isoWeek(d) {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const year = t.getUTCFullYear();
  const week = Math.ceil(((t - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7);
  return year + "-W" + String(week).padStart(2, "0");
}
const week = (offset) => isoWeek(new Date(Date.now() + offset * 7 * 86400000));
const PLANS = [
  { name: "Métropole lilloise", departments: ["59"], weeks: [week(0), week(1), week(3)], color: 2 },
  { name: "Aisne et Ardennes", departments: ["02", "08"], weeks: [week(-1), week(2)], color: 5 },
];

const current = await call("commercial", "get_tour_plans", {}, "site");
const existing = new Map((current.plans || []).map((p) => [p.name, p]));
for (const plan of PLANS) {
  const found = existing.get(plan.name);
  const args = { idempotency_key: "studio-plan-" + plan.name + "-" + Date.now(), data: plan };
  if (found) { args.id = found.id; args.expected_revision = found.revision; }
  const saved = await call("commercial", "save_tour_plan", args, "site");
  console.log((found ? "Mis à jour : " : "Créé : ") + saved.plan.name + " · " + saved.plan.weeks.map((w) => w.week ?? w.id ?? JSON.stringify(w)).join(", "));
}

