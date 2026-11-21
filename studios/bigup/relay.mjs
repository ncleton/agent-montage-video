#!/usr/bin/env node
// Relais d'identité du studio Bigup : pose devant le Site local (wrangler dev) les en-têtes que ChatGPT Sites
// pose en production, pour un compte fictif du studio. Aucun compte ChatGPT n'est utilisé.
//   node relay.mjs <port d'écoute> <port du Site> <personne>
// Personnes : commercial (compte de démonstration filmé, droits de base) et admin (réglage du studio seulement).
import http from "node:http";

const PEOPLE = {
  commercial: { id: "studio-commercial", email: "camille.martin@rossinienergy.com", name: "Camille Martin" },
  admin: { id: "studio-admin", email: "studio.admin@rossinienergy.com", name: "Studio Administration" },
};
const [listen, upstream, who] = [Number(process.argv[2]), Number(process.argv[3]), process.argv[4]];
const person = PEOPLE[who];
if (!listen || !upstream || !person) {
  console.error("Usage : node relay.mjs <port d'écoute> <port du Site> <" + Object.keys(PEOPLE).join("|") + ">");
  process.exit(2);
}

http.createServer((request, response) => {
  const headers = { ...request.headers, host: "127.0.0.1:" + upstream };
  for (const key of Object.keys(headers)) if (key.startsWith("oai-")) delete headers[key];
  headers["oai-authenticated-user-id"] = person.id;
  headers["oai-authenticated-user-email"] = person.email;
  headers["oai-authenticated-user-full-name"] = encodeURIComponent(person.name);
  headers["oai-authenticated-user-full-name-encoding"] = "percent-encoded-utf-8";
  const forward = http.request({ host: "127.0.0.1", port: upstream, method: request.method, path: request.url, headers }, (answer) => {
    response.writeHead(answer.statusCode || 502, answer.headers);
    answer.pipe(response);
  });
  forward.on("error", (error) => {
    response.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    response.end("Le Site local du studio ne répond pas sur le port " + upstream + " : " + error.message + ". Lancer studios/bigup/start.sh.");
  });
  request.pipe(forward);
}).listen(listen, "127.0.0.1", () => console.log("Relais " + who + " : http://127.0.0.1:" + listen + " -> Site 127.0.0.1:" + upstream));

