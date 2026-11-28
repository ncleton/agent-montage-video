// Restreint Chromium aux copies locales quand le parcours change de Site.
export function studioChromeOptions(scenario) {
  const network = scenario.localNetwork;
  // La langue de Chromium règle le format des champs d'heure. Sur macOS, Chromium de Playwright garde « 10:00 AM » ;
  // scenario.channel = "chrome" prend Google Chrome, qui suit la langue du Mac (« 10:00 »).
  const lang = "--lang=" + (scenario.locale ?? "fr-FR");
  const channel = scenario.channel ? { channel: scenario.channel } : {};
  if (!network) return { ...channel, args: [lang] };
  const entries = Object.entries(network.ports ?? {});
  if (!entries.length || !/^[A-Za-z0-9+/]{43}=$/.test(network.spki ?? "")) {
    throw new Error("Réseau du studio : renseignez les origines et l’empreinte TLS locale.");
  }
  const rules = entries.map(([host, port]) => {
    if (!/^[a-z0-9.-]+$/.test(host) || !Number.isInteger(port) || port < 1024 || port > 65535) {
      throw new Error("Origine du studio invalide : " + host);
    }
    return `MAP ${host} 127.0.0.1:${port}`;
  });
  rules.push("MAP * ~NOTFOUND", "EXCLUDE localhost");
  return {
    ...channel,
    args: [
      lang,
      "--disable-background-networking",
      "--no-proxy-server",
      "--host-resolver-rules=" + rules.join(","),
      "--ignore-certificate-errors-spki-list=" + network.spki,
    ],
  };
}

// Cache disque des images publiques qu'un écran charge par rafales (orthophotos IGN du Tableur, Nicolas 21/11/2026) :
// le Géoportail refuse parfois une rafale et l'écran affiche « Image IGN indisponible » sur une ligne au hasard.
// scenario.cache = { "dir": "work/cache-images", "hosts": ["data\\.geopf\\.fr"] } : chaque image est demandée une fois,
// avec des essais espacés, gardée sur le disque, puis servie à l'identique au contrôle comme au tournage.
export async function studioCache(context, scenario) {
  const cache = scenario.cache;
  if (!cache) return;
  const { mkdirSync, existsSync, readFileSync, writeFileSync } = await import("node:fs");
  const { join, resolve } = await import("node:path");
  const { createHash } = await import("node:crypto");
  const dir = resolve(cache.dir ?? "work/cache-images");
  mkdirSync(dir, { recursive: true });
  const hosts = new RegExp("^https?://(?:" + (cache.hosts ?? ["data\\.geopf\\.fr"]).join("|") + ")/");
  await context.route((url) => hosts.test(url.href), async (route) => {
    const key = createHash("sha256").update(route.request().url()).digest("hex");
    const body = join(dir, key + ".bin"), meta = join(dir, key + ".json");
    if (existsSync(body) && existsSync(meta)) {
      const m = JSON.parse(readFileSync(meta, "utf8"));
      return route.fulfill({ status: 200, contentType: m.contentType, body: readFileSync(body), headers: { "access-control-allow-origin": "*" } });
    }
    let last = "";
    for (let attempt = 0; attempt < 6; attempt++) {
      try {
        const res = await route.fetch({ timeout: 30000 });
        const type = res.headers()["content-type"] ?? "";
        if (res.ok() && type.startsWith("image/")) {
          const buffer = await res.body();
          writeFileSync(body, buffer);
          writeFileSync(meta, JSON.stringify({ url: route.request().url(), contentType: type }));
          return route.fulfill({ status: 200, contentType: type, body: buffer, headers: { "access-control-allow-origin": "*" } });
        }
        last = res.status() + " " + type;
      } catch (e) { last = e.message.split("\n")[0]; }
      await new Promise((r) => setTimeout(r, 800 * (attempt + 1) + Math.random() * 600));
    }
    console.error("cache d'images : " + route.request().url().slice(0, 160) + " refusée six fois (" + last + ")");
    return route.continue();
  });
}


// Heure du studio (scenario.now, date ISO avec fuseau) : la page voit cette heure, qui avance ensuite normalement.
// Un tournage du soir montrait « Journée terminée » au lieu d'une journée de travail (26/11/2026). Seul Date est
// décalé ; les minuteurs, requestAnimationFrame et performance.now restent ceux du navigateur, la carte ne bouge pas.
export async function studioClock(context, scenario) {
  if (!scenario.now) return;
  const target = Date.parse(scenario.now);
  if (!Number.isFinite(target)) throw new Error("scenario.now illisible : " + scenario.now);
  await context.addInitScript((wanted) => {
    const Real = Date, offset = wanted.target - wanted.started; // décalage fixé à l'ouverture du contexte
    class Shifted extends Real {
      constructor(...a) { if (a.length) super(...a); else super(Real.now() + offset); }
      static now() { return Real.now() + offset; }
    }
    Shifted.parse = Real.parse; Shifted.UTC = Real.UTC;
    globalThis.Date = Shifted;
  }, { target, started: Date.now() });
}

// Textes retirés de l'image (scenario.hideTexts : débuts de texte) : un message d'information de l'outil que la personne
// qui commande ne veut pas voir dans le tutoriel (Nicolas, Retake du 28/11/2026 sur le bandeau des Plans de tournée :
// « supprime ce message »). Le plus petit élément dont le texte commence ainsi est masqué dès qu'il apparaît ; la page
// se met en page sans lui, comme s'il n'existait pas. Contrôle et tournage le masquent de la même façon.
export async function studioHide(context, scenario) {
  const texts = (scenario.hideTexts ?? []).filter(Boolean);
  if (!texts.length) return;
  await context.addInitScript((wanted) => {
    let queued = false;
    const sweep = () => {
      queued = false;
      if (!document.body) return;
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const start = n.textContent.trim();
        if (!start || !wanted.some((w) => start.startsWith(w))) continue;
        let el = n.parentElement;
        // Remonter jusqu'au bloc du message : son texte entier commence encore ainsi, son parent non.
        while (el.parentElement && el.parentElement !== document.body && wanted.some((w) => el.parentElement.innerText.trim().startsWith(w))) el = el.parentElement;
        if (el.style.display !== "none") el.style.setProperty("display", "none", "important");
      }
    };
    const queue = () => { if (!queued) { queued = true; requestAnimationFrame(sweep); } };
    new MutationObserver(queue).observe(document, { childList: true, subtree: true, characterData: true });
    document.addEventListener("DOMContentLoaded", queue);
  }, texts);
}
