// Appel signé de la plateforme du studio au nom d'un compte du studio (sub et e-mail), comme le Site le signe.
// Refuse toute adresse autre que 127.0.0.1 : il ne parle qu'au studio.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const DATA = fileURLToPath(new URL("../data/", import.meta.url));
const SERVICE = "http://127.0.0.1:55811";

export async function as(person, tool, args) {
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
  const response = await fetch(SERVICE + "/v1/call", { method: "POST", body,
    headers: { "Content-Type": "application/json", "X-Leadgenerator-Assertion": encoded + "." + signature } });
  const value = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(tool + " : " + response.status + " " + JSON.stringify(value.error ?? value));
  return value.result;
}

