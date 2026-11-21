// Lance la route d’accès du CRM au commit déployé, avec son Supabase REST local.
import http from "node:http";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { readFileSync } from "node:fs";

const crm = new URL("./data/crm/mcp-server/", import.meta.url);
const require = createRequire(new URL("package.json", crm));
const { Hono } = require("hono");
const { serve } = require("@hono/node-server");
const { default: access } = await import(pathToFileURL(fileURLToPath(new URL("src/http/routes/rossini-site-auth.ts", crm))).href);
const localPostgrest = 55831;
const restCompat = 55830;
const base = "/rest/v1/";
process.env.CRM_ADMIN_SECRET = readFileSync(new URL("./data/crm-secret", import.meta.url), "utf8").trim();
process.env.SUPABASE_URL = `http://127.0.0.1:${restCompat}`;
process.env.SUPABASE_SERVICE_KEY = readFileSync(new URL("./data/gateway-secret", import.meta.url), "utf8").trim();

http.createServer((request, response) => {
  if (!request.url?.startsWith(base + "rossini_crm_access")) {
    response.writeHead(404).end("Seules les tables d’accès CRM sont ouvertes dans ce studio.");
    return;
  }
  const headers = { ...request.headers };
  delete headers.authorization;
  delete headers.apikey;
  const rest = http.request({
    host: "127.0.0.1",
    port: localPostgrest,
    path: "/" + request.url.slice(base.length),
    method: request.method,
    headers,
  }, (answer) => {
    response.writeHead(answer.statusCode ?? 502, answer.headers);
    answer.pipe(response);
  });
  rest.on("error", () => response.writeHead(502).end("PostgREST du studio indisponible."));
  request.pipe(rest);
}).listen(restCompat, "127.0.0.1");

const app = new Hono();
app.route("/api/auth/site", access);
app.onError((error, context) => context.json({ error: error.message }, error.status ?? 500));
serve({ fetch: app.fetch, port: 55829, hostname: "127.0.0.1" });
