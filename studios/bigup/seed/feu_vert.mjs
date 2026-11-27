#!/usr/bin/env node
// La réponse du chargé d'affaires à une demande de feu vert, pendant un tournage (Nicolas, 27/11/2026) : Thibaut
// Gourlin, chargé d'affaires du client Dubois Promotion dans le studio, autorise l'appel par l'action de Bigup qu'il
// aurait cliquée (« Autoriser l'appel », set_colleague_request go), avec son propre compte du studio.
//   node seed/feu_vert.mjs [go|intro|later]
// Échoue s'il n'a aucune demande en attente : le tournage s'arrête au lieu de filmer une fiche sans feu vert.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { as } from "./as.mjs";

const DATA = fileURLToPath(new URL("../data/", import.meta.url));
const answer = process.argv[2] ?? "go";
if (!["go", "intro", "later"].includes(answer)) { console.error("usage : node seed/feu_vert.mjs [go|intro|later]"); process.exit(2); }
const thibaut = JSON.parse(readFileSync(DATA + "team.json", "utf8")).members.find((m) => m.sub === "studio-thibaut");
if (!thibaut) { console.error("Thibaut Gourlin absent de data/team.json."); process.exit(1); }
const { requests } = await as(thibaut, "get_colleague_requests", { data: {} });
const request = requests.find((r) => r.answer === "waiting");
if (!request) { console.error("Aucune demande de feu vert en attente pour Thibaut Gourlin."); process.exit(1); }
await as(thibaut, "set_colleague_request", { idempotency_key: crypto.randomUUID(),
  data: { siren: request.siren, client_row_id: request.client_row_id, action: answer, expected: request.id } });
console.log("Feu vert de Thibaut Gourlin pour " + request.prospect + " (" + request.client + ") : " + answer);

