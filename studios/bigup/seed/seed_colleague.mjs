#!/usr/bin/env node
// Un collègue fictif du studio, Théo Marchand, chargé d'affaires avec sa propre zone de tournée (Ardennes et Marne,
// hors des zones de Camille) : il reçoit les fiches transférées (« Transférer », interrupteur vente.transfert_prospect).
// Sa première connexion crée son compte commercial ; l'administrateur du studio lui donne sa zone. Relançable.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { call } from "./call.mjs";

const COLLEAGUE = { sub: "studio-charge", email: "theo.marchand@rossinienergy.com" };
const DATA = fileURLToPath(new URL("../data/", import.meta.url));

async function as(person, tool, args) {
  const secret = readFileSync(DATA + "gateway-secret", "utf8").trim();
  const encoder = new TextEncoder();
  const body = JSON.stringify({ tool, arguments: args });
  const hex = (b) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
  const payload = { sub: person.sub, email: person.email, workspace: "studio-bigup", site: "studio-bigup-site", surface: "site",
    iat: Math.floor(Date.now() / 1000), nonce: crypto.randomUUID(), method: "POST", path: "/v1/call",
    body_hash: hex(await crypto.subtle.digest("SHA-256", encoder.encode(body))) };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = hex(await crypto.subtle.sign("HMAC", key, encoder.encode(encoded)));
  const response = await fetch("http://127.0.0.1:55811/v1/call", { method: "POST", body,
    headers: { "Content-Type": "application/json", "X-Leadgenerator-Assertion": encoded + "." + signature } });
  const value = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(tool + " : " + response.status + " " + JSON.stringify(value.error ?? value));
  return value.result;
}

await as(COLLEAGUE, "get_current_actor", {});
// Les mêmes accès de base que Camille, la commerciale de démonstration.
const ROUTES = { tours: "write", "contact-quick": "write", "company-quick": "write" };
const member = (await call("admin", "list_members", {}, "site")).members.find((m) => m.subject === COLLEAGUE.sub);
const same = (a, b) => Object.keys(a).length === Object.keys(b).length && Object.entries(a).every(([k, v]) => b[k] === v);
if (!same(member?.routes ?? {}, ROUTES)) {
  await call("admin", "manage_member_access", { idempotency_key: "studio-theo-access-" + Date.now(),
    data: { subject: COLLEAGUE.sub, routes: ROUTES } }, "site");
}
const home = await as(COLLEAGUE, "get_sales_home", {});
// Une première zone s'écrit sans révision attendue (0, absente du schéma).
const revision = home?.home?.revision;
await call("admin", "manage_sales_home", { idempotency_key: "studio-zone-theo-" + Date.now(), ...(revision ? { expected_revision: revision } : {}),
  data: { email: COLLEAGUE.email, zone_label: "Agence Reims", departments: ["08", "51"] } });
console.log("Collègue du studio prêt : " + COLLEAGUE.email + ", zone Ardennes et Marne.");

