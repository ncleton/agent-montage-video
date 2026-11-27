#!/usr/bin/env node
// Les collègues réels du studio (Nicolas, 27/11/2026) : un compte commercial chacun, aux mêmes accès de base que
// Camille, et une zone de tournée hors des zones de Camille. Ils deviennent ainsi destinataires de « Transférer », et
// le chargé d'affaires du client d'un prospect en or peut donner son feu vert. Leurs noms, e-mails et photos Slack
// sont dans data/team.json (hors Git) ; seed/seed_team.py pose leurs photos et l'annuaire des propriétaires.
//   node seed/seed_team.mjs                 crée ou met à jour les comptes et les zones (relançable)
//   node seed/seed_team.mjs --theo on|off   livrets de Théo Marchand (collègue fictif) allumés ou éteints : éteints,
//                                           il ne figure plus parmi les destinataires de « Transférer »
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { call } from "./call.mjs";
import { as } from "./as.mjs";

const DATA = fileURLToPath(new URL("../data/", import.meta.url));
const ROUTES = { tours: "write", "contact-quick": "write", "company-quick": "write" };
const same = (a, b) => Object.keys(a).length === Object.keys(b).length && Object.entries(a).every(([k, v]) => b[k] === v);

const args = process.argv.slice(2);
if (args[0] === "--theo") {
  if (!["on", "off"].includes(args[1])) { console.error("usage : node seed/seed_team.mjs --theo on|off"); process.exit(2); }
  await call("admin", "manage_automation", { data: { automation: "monthly_books", step: "save_settings",
    settings: { people: { "theo.marchand@rossinienergy.com": args[1] === "on" } } } }, "site");
  console.log("Livrets de Théo Marchand " + (args[1] === "on" ? "rallumés." : "éteints pour le tournage."));
  process.exit(0);
}
const { members } = JSON.parse(readFileSync(DATA + "team.json", "utf8"));
for (const person of members) {
  await as(person, "get_current_actor", {});
  const member = (await call("admin", "list_members", {}, "site")).members.find((m) => m.subject === person.sub);
  if (!same(member?.routes ?? {}, ROUTES)) {
    await call("admin", "manage_member_access", { idempotency_key: "studio-access-" + person.sub + "-" + Date.now(), data: { subject: person.sub, routes: ROUTES } }, "site");
  }
  const home = await as(person, "get_sales_home", {});
  const revision = home?.home?.revision;
  await call("admin", "manage_sales_home", { idempotency_key: "studio-zone-" + person.sub + "-" + Date.now(), ...(revision ? { expected_revision: revision } : {}),
    data: { email: person.email, zone_label: "Zone de démonstration", departments: person.departments } });
  console.log("Collègue du studio prêt : " + person.first_name + " " + person.last_name);
}

