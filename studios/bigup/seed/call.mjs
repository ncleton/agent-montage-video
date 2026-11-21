#!/usr/bin/env node
// Appel signé d'un outil de la plateforme du studio, comme le Site le signe (lib/platform-service.mjs, signedRequest),
// avec le secret du studio : node call.mjs <admin|commercial> <outil> '<arguments JSON>' [surface]
// Refuse toute adresse autre que 127.0.0.1 : il ne peut parler qu'au studio.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PEOPLE = {
  admin: { sub: "studio-admin", email: "studio.admin@rossinienergy.com" },
  commercial: { sub: "studio-commercial", email: "camille.martin@rossinienergy.com" },
};
const DATA = fileURLToPath(new URL("../data/", import.meta.url));
const SERVICE = "http://127.0.0.1:55811";

export async function call(who, tool, args = {}, surface = "mcp") {
  const person = PEOPLE[who];
  if (!person) throw new Error("Personne inconnue : " + who);
  const secret = readFileSync(DATA + "gateway-secret", "utf8").trim();
  const encoder = new TextEncoder();
  const body = JSON.stringify({ tool, arguments: args });
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(body));
  const hex = (buffer) => [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
  const payload = { sub: person.sub, email: person.email, workspace: "studio-bigup", site: "studio-bigup-site", surface,
    iat: Math.floor(Date.now() / 1000), nonce: crypto.randomUUID(), method: "POST", path: "/v1/call", body_hash: hex(digest) };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = hex(await crypto.subtle.sign("HMAC", key, encoder.encode(encoded)));
  const response = await fetch(SERVICE + "/v1/call", { method: "POST", body,
    headers: { "Content-Type": "application/json", "X-Leadgenerator-Assertion": encoded + "." + signature } });
  const value = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(tool + " : " + response.status + " " + JSON.stringify(value.error ?? value));
  return value.result;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [who, tool, raw, surface] = process.argv.slice(2);
  call(who, tool, raw ? JSON.parse(raw) : {}, surface || "mcp")
    .then((result) => console.log(JSON.stringify(result, null, 2)))
    .catch((error) => { console.error(error.message); process.exit(1); });
}

