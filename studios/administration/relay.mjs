// Identité du studio et relais TLS vers les services locaux. Les origines des
// deux Sites restent distinctes pour leur vraie navigation et leurs cookies.
import http from "node:http";
import https from "node:https";
import { readFileSync } from "node:fs";

const data = new URL("./data/", import.meta.url);
const tls = {
  cert: readFileSync(new URL("studio-cert.pem", data)),
  key: readFileSync(new URL("studio-key.pem", data)),
};
const sites = [
  { port: 55824, upstream: 55821, hostname: "ad.rossinienergy.com", actor: "studio-admin" },
  { port: 55825, upstream: 55822, hostname: "learning.rossinienergy.com", actor: "studio-admin" },
  { port: 55826, upstream: 55828, hostname: "127.0.0.1" },
  { port: 55827, upstream: 55829, hostname: "127.0.0.1" },
  { port: 55832, upstream: 55836, hostname: "127.0.0.1" },
];

for (const site of sites) {
  https.createServer(tls, (request, response) => {
    const requestHost = (request.headers.host ?? "").split(":")[0];
    if (requestHost !== site.hostname || !request.url?.startsWith("/") || request.url.startsWith("//")) {
      response.writeHead(421).end("Origine du studio inconnue.");
      return;
    }
    const headers = { ...request.headers, host: `127.0.0.1:${site.upstream}` };
    for (const name of Object.keys(headers)) {
      if (name.startsWith("oai-") || name === "x-forwarded-host") delete headers[name];
    }
    if (site.actor) {
      headers["oai-authenticated-user-id"] = site.actor;
      headers["oai-authenticated-user-email"] = "admin.video@example.com";
      headers["oai-authenticated-user-full-name"] = encodeURIComponent("Administration studio");
      headers["oai-authenticated-user-full-name-encoding"] = "percent-encoded-utf-8";
    }
    const upstream = http.request({
      host: "127.0.0.1",
      port: site.upstream,
      path: request.url,
      method: request.method,
      headers,
    }, (answer) => {
      response.writeHead(answer.statusCode ?? 502, answer.headers);
      answer.pipe(response);
    });
    upstream.on("error", (error) => {
      response.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
      response.end(`Le service du studio sur ${site.upstream} ne répond pas : ${error.code}.`);
    });
    request.pipe(upstream);
  }).listen(site.port, "127.0.0.1");
}
