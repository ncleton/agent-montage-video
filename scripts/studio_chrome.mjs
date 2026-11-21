// Restreint Chromium aux copies locales quand le parcours change de Site.
export function studioChromeOptions(scenario) {
  const network = scenario.localNetwork;
  if (!network) return {};
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
    args: [
      "--disable-background-networking",
      "--no-proxy-server",
      "--host-resolver-rules=" + rules.join(","),
      "--ignore-certificate-errors-spki-list=" + network.spki,
    ],
  };
}
