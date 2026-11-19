import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C, Visual, clamp, ease, fadeIn } from "./theme";
import { loadFont } from "@remotion/google-fonts/Inter";
import script from "./script.json";
import audio from "./audio.json";
import { DIAGRAMS } from "./diagrams";

export const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin", "latin-ext"] });

/* ---------- types ---------- */
type Word = { t: string; s: number; e: number };
type Cue = { text: string; start: number; end: number };
type Voice = { file: string; durationSec: number; words: Word[]; cues: Cue[] };
type CamKey = { at: string | null; s: number; x: number; y: number };
type Hl = { box: number[]; at: string; until?: string; label?: string; side?: "top" | "bottom" | "left" | "right" };
export type Shot = { capture: string; tc: string; at: string | null; cam?: CamKey[]; hl?: Hl[]; caption?: string };
export type Scene = { id: string; chapter: string; passage: string; narration: string; concepts?: string[]; shots?: Shot[]; visual?: Visual; holdSec?: number };
type Chapter = { id: string; title: string; n: number };

const S = script as unknown as {
  fps: number; width: number; height: number; leadSec: number; gapSec: number; tailSec: number;
  meeting: { title: string; date: string; label: string };
  capture: { w: number; h: number };
  chapters: Chapter[]; scenes: Scene[];
};
const V = (audio as { voice: Record<string, Voice> }).voice;
export const FPS = S.fps;
const XFADE = 0.4;

/* ---------- timing ---------- */
const norm = (t: string) => t.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const toks = (t: string) => norm(t).match(/[a-z0-9]+/g) ?? [];

export const layout = (() => {
  let t = 0;
  return S.scenes.map((s, i) => {
    const v = V[s.id];
    if (!v) throw new Error("Voix absente pour la scène " + s.id + " : relancer split_voice.py");
    const lead = i === 0 ? S.leadSec : 0.15;
    const tail = (i === S.scenes.length - 1 ? S.tailSec : S.gapSec) + (s.holdSec ?? 0);
    const dur = lead + v.durationSec + tail;
    const r = { scene: s, start: t, lead, dur, index: i };
    t += dur;
    return r;
  });
})();
export const totalFrames = () => Math.round(layout.reduce((a, l) => a + l.dur, 0) * FPS);

/** Seconds from scene start of the spoken word matching "keyword" or "keyword#n" (n-th occurrence). */
export function wordAt(sceneId: string, lead: number, key: string | null | undefined): number {
  if (!key) return 0;
  const [kw, nth] = key.split("#");
  const want = toks(kw);
  const words = V[sceneId].words;
  let seen = 0;
  for (let i = 0; i < words.length; i++) {
    const ok = want.every((w, j) => words[i + j] && toks(words[i + j].t).join("").startsWith(w));
    if (ok && ++seen === Number(nth ?? 1)) return lead + words[i].s;
  }
  throw new Error("Mot déclencheur introuvable dans la voix : " + sceneId + " / " + key);
}

export type Ctx = { t: number; at: (k: string | null | undefined) => number; dur: number; scene: Scene };

/* ---------- brand ---------- */
const Logo: React.FC<{ h: number }> = ({ h }) => <Img src={staticFile("brand/rossini-re.png")} style={{ height: h, width: "auto", display: "block" }} />;

const ChapterCard: React.FC<{ ctx: Ctx; v: Visual }> = ({ ctx, v }) => {
  const ch = S.chapters.find((c) => c.id === ctx.scene.chapter)!;
  const t = ctx.t;
  const o = fadeIn(t, 0, 0.5);
  const y = interpolate(t, [0, 0.8], [30, 0], { ...clamp, easing: ease });
  const bar = interpolate(t, [0.2, 1.1], [0, 1], { ...clamp, easing: ease });
  const intro = v.intro as boolean | undefined;
  return (
    <AbsoluteFill style={{ background: C.bg, alignItems: "flex-start", justifyContent: "center", paddingLeft: 190 }}>
      <div style={{ opacity: o, transform: "translateY(" + y + "px)", color: C.ink }}>
        {intro ? <Logo h={120} /> : <div style={{ fontSize: 180, fontWeight: 800, color: C.red, lineHeight: 1, letterSpacing: -6 }}>{String(ch.n).padStart(2, "0")}</div>}
        <div style={{ height: 8, width: 220 * bar, background: C.red, borderRadius: 4, margin: "34px 0 30px" }} />
        <div style={{ fontSize: intro ? 86 : 78, fontWeight: 800, letterSpacing: -2, maxWidth: 1450, lineHeight: 1.06 }}>{(v.title as string) ?? ch.title}</div>
        {v.subtitle ? <div style={{ fontSize: 38, fontWeight: 500, color: C.sub, marginTop: 22, maxWidth: 1400 }}>{v.subtitle as string}</div> : null}
        {intro ? <div style={{ fontSize: 26, fontWeight: 600, color: C.sub, marginTop: 40 }}>{S.meeting.label}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- capture of the recording ---------- */
const CAP_W = 1340;
const CAP_H = Math.round((CAP_W * S.capture.h) / S.capture.w);
const CAP_X = (1920 - CAP_W) / 2;
const CAP_Y = 128;

function camAt(t: number, keys: { t: number; s: number; x: number; y: number }[]) {
  let cur = { s: 1, x: 0.5, y: 0.5 };
  for (const k of keys) {
    if (t < k.t) break;
    const p = ease(Math.min(1, (t - k.t) / 1.0));
    const prev = cur;
    cur = { s: prev.s + (k.s - prev.s) * p, x: prev.x + (k.x - prev.x) * p, y: prev.y + (k.y - prev.y) * p };
  }
  const tx = Math.min(0, Math.max(CAP_W - CAP_W * cur.s, CAP_W / 2 - cur.x * CAP_W * cur.s));
  const ty = Math.min(0, Math.max(CAP_H - CAP_H * cur.s, CAP_H / 2 - cur.y * CAP_H * cur.s));
  return { s: cur.s, tx, ty };
}

const hlOpacity = (t: number, t0: number, t1: number) => Math.min(fadeIn(t, t0, 0.35), interpolate(t, [t1 - 0.3, t1], [1, 0], clamp));

/** Box drawn inside the zoomed layer; its label is drawn by HlLabel in screen space. */
const Highlight: React.FC<{ h: Hl; t: number; t0: number; t1: number; scale: number }> = ({ h, t, t0, t1, scale }) => {
  const k = CAP_W / S.capture.w;
  const o = hlOpacity(t, t0, t1);
  if (o <= 0) return null;
  const [x1, y1, x2, y2] = h.box;
  const pad = 6 / scale;
  const grow = interpolate(o, [0, 1], [12, 0]) / scale;
  return (
    <div style={{ position: "absolute", left: x1 * k - pad - grow, top: y1 * k - pad - grow, width: (x2 - x1) * k + 2 * (pad + grow), height: (y2 - y1) * k + 2 * (pad + grow), borderRadius: 10 / scale, border: (4 / scale) + "px solid " + C.red, boxShadow: "0 0 0 9999px rgba(20,24,32," + 0.28 * o + ")", opacity: o }} />
  );
};

/** Label of a highlight, in screen space, kept inside the capture frame. */
const HlLabel: React.FC<{ h: Hl; o: number; cam: { s: number; tx: number; ty: number } }> = ({ h, o, cam }) => {
  if (!h.label || o <= 0) return null;
  const k = (CAP_W / S.capture.w) * cam.s;
  const [x1, y1, x2, y2] = h.box;
  const L = Math.max(0, x1 * k + cam.tx), T = Math.max(0, y1 * k + cam.ty);
  const R = Math.min(CAP_W, x2 * k + cam.tx), B = Math.min(CAP_H, y2 * k + cam.ty);
  let side = h.side ?? "bottom";
  if (side === "right" && CAP_W - R < 380) side = L > 380 ? "left" : "top";
  if (side === "left" && L < 380) side = CAP_W - R > 380 ? "right" : "top";
  if (side === "bottom" && CAP_H - B < 60) side = "top";
  if (side === "top" && T < 60) side = "bottom";
  const pos: React.CSSProperties = {};
  if (side === "top" || side === "bottom") {
    if ((L + R) / 2 > CAP_W / 2) pos.right = Math.max(10, CAP_W - R); else pos.left = Math.max(10, L);
    if (side === "top") pos.bottom = Math.min(CAP_H - 50, CAP_H - T + 10); else pos.top = Math.min(CAP_H - 50, B + 10);
  } else {
    pos.top = Math.min(CAP_H - 50, Math.max(10, T));
    if (side === "right") pos.left = R + 14; else pos.right = CAP_W - L + 14;
  }
  return (
    <div style={{ position: "absolute", ...pos, maxWidth: 560, background: C.red, color: "#fff", fontWeight: 700, fontSize: 26, padding: "8px 16px", borderRadius: 10, opacity: o, boxShadow: "0 6px 18px rgba(0,0,0,.25)" }}>{h.label}</div>
  );
};

const CaptureView: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { t, at, dur, scene } = ctx;
  const shots = scene.shots!.map((sh, i) => ({ sh, t0: i === 0 ? 0 : at(sh.at) }));
  const active = shots.reduce((a, x, i) => (t >= x.t0 ? i : a), 0);
  const enter = spring({ frame: Math.round(t * FPS), fps: FPS, config: { damping: 200 }, durationInFrames: 30 });
  const cur = shots[active].sh;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: CAP_X, top: CAP_Y, width: CAP_W, height: CAP_H, borderRadius: 16, overflow: "hidden", boxShadow: "0 24px 70px rgba(20,24,32,.28)", background: "#111", transform: "scale(" + (0.96 + 0.04 * enter) + ")", opacity: enter }}>
        {shots.map(({ sh, t0 }, i) => {
          const t1 = i + 1 < shots.length ? shots[i + 1].t0 : dur + 1;
          if (t < t0 - 0.01 || t > t1 + 0.5) return null;
          const o = i === 0 ? 1 : fadeIn(t, t0, 0.45);
          const keys = (sh.cam ?? []).map((c) => ({ t: c.at ? at(c.at) : t0, s: c.s, x: c.x, y: c.y }));
          const c = camAt(t, keys);
          return (
            <div key={i} style={{ position: "absolute", inset: 0, opacity: o }}>
              <div style={{ position: "absolute", left: 0, top: 0, width: CAP_W, height: CAP_H, transformOrigin: "0 0", transform: "translate(" + c.tx + "px," + c.ty + "px) scale(" + c.s + ")" }}>
                <Img src={staticFile("captures/" + sh.capture.replace(/\.jpg$/, ".png"))} style={{ width: CAP_W, height: CAP_H, display: "block" }} />
                {(sh.hl ?? []).map((h, j) => <Highlight key={j} h={h} t={t} t0={at(h.at)} t1={Math.min(h.until ? at(h.until) : t1, t1)} scale={c.s} />)}
              </div>
              {(sh.hl ?? []).map((h, j) => <HlLabel key={"l" + j} h={h} cam={c} o={hlOpacity(t, at(h.at), Math.min(h.until ? at(h.until) : t1, t1))} />)}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: CAP_X, top: CAP_Y + CAP_H + 16, display: "flex", alignItems: "center", gap: 14, fontSize: 22, color: C.sub, fontWeight: 600, opacity: enter }}>
        <span style={{ background: C.ink, color: "#fff", borderRadius: 8, padding: "5px 12px", fontVariantNumeric: "tabular-nums" }}>Réunion · {cur.tc}</span>
        <span>{cur.caption ?? "Capture de l'écran partagé pendant la réunion"}</span>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- generic motion cards ---------- */
type Item = { text: string; at: string; tone?: "ok" | "warn" | "no"; sub?: string };
const Checklist: React.FC<{ ctx: Ctx; v: Visual }> = ({ ctx, v }) => {
  const items = v.items as Item[];
  return (
    <AbsoluteFill style={{ background: C.bg, padding: "190px 200px 0" }}>
      <div style={{ fontSize: 58, fontWeight: 800, color: C.ink, letterSpacing: -1, marginBottom: 46 }}>{v.title as string}</div>
      {items.map((it, i) => {
        const a = ctx.at(it.at);
        const o = fadeIn(ctx.t, a, 0.45);
        const col = it.tone === "warn" ? C.amber : it.tone === "no" ? C.red : it.tone === "ok" ? C.green : C.red;
        return (
          <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 28, marginBottom: 30, opacity: o, transform: "translateX(" + (1 - o) * -30 + "px)" }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: col, marginTop: 14, flex: "none" }} />
            <div>
              <div style={{ fontSize: 44, fontWeight: 700, color: C.ink, lineHeight: 1.2 }}>{it.text}</div>
              {it.sub ? <div style={{ fontSize: 30, color: C.sub, marginTop: 6, fontWeight: 500 }}>{it.sub}</div> : null}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

type Fig = { value: string; unit?: string; label: string; at: string; color?: string };
const Figures: React.FC<{ ctx: Ctx; v: Visual }> = ({ ctx, v }) => {
  const figs = v.figures as Fig[];
  return (
    <AbsoluteFill style={{ background: C.bg, alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
      {v.title ? <div style={{ fontSize: 54, fontWeight: 800, color: C.ink, marginBottom: 70, letterSpacing: -1 }}>{v.title as string}</div> : null}
      <div style={{ display: "flex", gap: 60 }}>
        {figs.map((f, i) => {
          const o = fadeIn(ctx.t, ctx.at(f.at), 0.5);
          return (
            <div key={i} style={{ width: 460, padding: "48px 40px", background: C.card, borderRadius: 26, boxShadow: "0 18px 50px rgba(20,24,32,.10)", opacity: o, transform: "translateY(" + (1 - o) * 30 + "px)", textAlign: "center" }}>
              <div style={{ fontSize: 120, fontWeight: 800, color: f.color ?? C.red, letterSpacing: -4, lineHeight: 1 }}>{f.value}<span style={{ fontSize: 52, marginLeft: 10, letterSpacing: 0 }}>{f.unit}</span></div>
              <div style={{ fontSize: 32, fontWeight: 600, color: C.sub, marginTop: 22, lineHeight: 1.25 }}>{f.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

type Line = { text: string; at: string; big?: boolean; color?: string };
const Formula: React.FC<{ ctx: Ctx; v: Visual }> = ({ ctx, v }) => {
  const lines = v.lines as Line[];
  return (
    <AbsoluteFill style={{ background: C.bg, padding: "190px 200px 0" }}>
      <div style={{ fontSize: 54, fontWeight: 800, color: C.ink, letterSpacing: -1, marginBottom: 56 }}>{v.title as string}</div>
      {lines.map((l, i) => {
        const o = fadeIn(ctx.t, ctx.at(l.at), 0.45);
        return <div key={i} style={{ fontSize: l.big ? 76 : 50, fontWeight: l.big ? 800 : 600, color: l.color ?? C.ink, marginBottom: l.big ? 40 : 26, opacity: o, transform: "translateY(" + (1 - o) * 20 + "px)", fontVariantNumeric: "tabular-nums", letterSpacing: l.big ? -1.5 : -0.5 }}>{l.text}</div>;
      })}
    </AbsoluteFill>
  );
};

/* ---------- frame chrome ---------- */
const Header: React.FC<{ scene: Scene; t: number }> = ({ scene, t }) => {
  const ch = S.chapters.find((c) => c.id === scene.chapter)!;
  if (scene.visual?.type === "chapter") return null;
  const o = fadeIn(t, 0, 0.3);
  return (
    <div style={{ position: "absolute", left: 210, right: 210, top: 44, height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", opacity: o }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <Logo h={44} />
        <div style={{ width: 2, height: 34, background: C.line }} />
        <span style={{ fontSize: 26, fontWeight: 800, color: C.red }}>{String(ch.n).padStart(2, "0")}</span>
        <span style={{ fontSize: 26, fontWeight: 700, color: C.ink }}>{ch.title}</span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {S.chapters.filter((c) => c.n > 0).map((c) => <div key={c.id} style={{ width: 34, height: 6, borderRadius: 3, background: c.n <= ch.n ? C.red : C.line }} />)}
      </div>
    </div>
  );
};

const Subtitles: React.FC<{ cues: Cue[]; t: number }> = ({ cues, t }) => {
  const c = cues.find((x) => t >= x.start && t < x.end);
  if (!c) return null;
  const o = Math.min(fadeIn(t, c.start, 0.15), interpolate(t, [c.end - 0.12, c.end], [1, 0], clamp));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 40, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ maxWidth: 1500, background: "rgba(29,35,44,.88)", color: "#fff", fontSize: 34, fontWeight: 600, lineHeight: 1.3, padding: "12px 26px", borderRadius: 12, textAlign: "center" }}>{c.text}</div>
    </div>
  );
};

const SceneView: React.FC<{ idx: number }> = ({ idx }) => {
  const frame = useCurrentFrame();
  const L = layout[idx];
  const t = frame / FPS;
  const scene = L.scene;
  const ctx: Ctx = { t, dur: L.dur, scene, at: (k) => (k ? wordAt(scene.id, L.lead, k) : 0) };
  const v = scene.visual;
  let body: React.ReactNode;
  if (scene.shots) body = <CaptureView ctx={ctx} />;
  else if (!v) throw new Error("Scène sans visuel : " + scene.id);
  else if (v.type === "chapter") body = <ChapterCard ctx={ctx} v={v} />;
  else if (v.type === "checklist") body = <Checklist ctx={ctx} v={v} />;
  else if (v.type === "figures") body = <Figures ctx={ctx} v={v} />;
  else if (v.type === "formula") body = <Formula ctx={ctx} v={v} />;
  else if (v.type === "diagram") {
    const D = DIAGRAMS[v.name as string];
    if (!D) throw new Error("Schéma inconnu : " + String(v.name));
    body = <D ctx={ctx} v={v} />;
  } else throw new Error("Type de visuel inconnu : " + v.type);
  const fadeOut = idx === layout.length - 1 ? interpolate(t, [L.dur - 0.6, L.dur], [1, 0], clamp) : 1;
  // crossfade: each scene fades in over the end of the previous one, which keeps running underneath
  const fadeInScene = idx === 0 ? 1 : interpolate(t, [0, XFADE], [0, 1], { ...clamp, easing: ease });
  return (
    <AbsoluteFill style={{ fontFamily, opacity: fadeOut * fadeInScene }}>
      {body}
      <Header scene={scene} t={t} />
      <Subtitles cues={V[scene.id].cues.map((c) => ({ ...c, start: c.start + L.lead, end: c.end + L.lead }))} t={t} />
      <Sequence from={Math.round(L.lead * FPS)}><Audio src={staticFile(V[scene.id].file)} /></Sequence>
    </AbsoluteFill>
  );
};

export const FormationVideo: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {layout.map((L, i) => (
        <Sequence key={L.scene.id} from={Math.round(L.start * fps)} durationInFrames={Math.round((L.start + L.dur + (i < layout.length - 1 ? XFADE : 0)) * fps) - Math.round(L.start * fps)}>
          <SceneView idx={i} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const meta = { fps: S.fps, width: S.width, height: S.height };
