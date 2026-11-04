// Chrome screencast recorder for Playwright: every frame is saved with its compositor timestamp, so
// retime_cast.py can build an exact 60 fps clip (no 25 fps recordVideo, no duplicated frames).
//   const c = await startCast(context, page, "work/casts/pli"); c.mark("scroll"); ...; await c.stop();
// Use a viewport of 1920x1080 and launch Chrome with --window-size=1920,1080, otherwise the frames are cropped.
import { mkdirSync, writeFileSync } from "node:fs";
export async function startCast(context, page, out) {
  mkdirSync(out, { recursive: true });
  const cdp = await context.newCDPSession(page);
  const frames = []; let i = 0;
  cdp.on("Page.screencastFrame", (f) => {
    const name = "f" + String(i++).padStart(5, "0") + ".jpg";
    writeFileSync(out + "/" + name, Buffer.from(f.data, "base64"));
    frames.push({ name, t: f.metadata.timestamp });
    cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 93, everyNthFrame: 1, maxWidth: 1920, maxHeight: 1080 });
  const wall0 = Date.now(); const marks = [];
  return {
    mark(label) { marks.push({ label, s: (Date.now() - wall0) / 1000 }); },
    async stop() { await cdp.send("Page.stopScreencast"); await new Promise((r) => setTimeout(r, 300)); writeFileSync(out + "/frames.json", JSON.stringify({ frames, marks })); return frames.length; },
  };
}
// Eased scroll of the nearest scrollable ancestor of a locator (crosses shadow roots); delta in px or "max".
export async function easeScrollFrom(locator, delta, ms) {
  return locator.evaluate(async (start, { delta, ms }) => {
    let e = start;
    const up = (x) => x.parentElement || (x.getRootNode() && x.getRootNode().host) || null;
    while (e) { const s = getComputedStyle(e); if (/(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 20) break; e = up(e); }
    if (!e) e = document.scrollingElement;
    const from = e.scrollTop, end = delta === "max" ? e.scrollHeight - e.clientHeight : from + delta;
    const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
    const t0 = performance.now();
    await new Promise((res) => { const step = (t) => { const k = Math.min(1, (t - t0) / ms); e.scrollTop = from + (end - from) * ease(k); if (k < 1) requestAnimationFrame(step); else res(); }; requestAnimationFrame(step); });
    return { from, end: e.scrollTop };
  }, { delta, ms });
}

