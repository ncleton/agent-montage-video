import React from "react";
import { AbsoluteFill, Audio, Freeze, Img, OffthreadVideo, Sequence, interpolate, Easing, spring, staticFile, useCurrentFrame, useVideoConfig, type CalculateMetadataFunction } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["500", "600", "700"], subsets: ["latin", "latin-ext"] });

type Cursor = { x: number; y: number; scale?: number };
type Timeline = { fps: number; width: number; height: number; zoom: number; frames: { cursor: Cursor }[]; events: { type: "click" | "key"; timeMs: number }[] };
type Key = { frame: number; scale: number; x: number; y: number };
export type Caption = { startMs: number; endMs: number; text: string };

// L'habillage d'un style : le fichier styles/<nom>/kit.json du dépôt, copié par scripts/studio_style.py avec ses
// images dans public/style/. Un nouveau style = un nouveau kit.json (styles/README.md).
export type Look = {
  name: string;
  frame: "rounded" | "pixel";
  background: string; halo?: string; grid?: string; gridOpacity?: number; floor?: string;
  window: string; ink: string; muted: string; accent: string; accent2?: string; onAccent?: string;
  bezel?: { outline: string; body: string; shade: string; light: string; screen: string };
  dialog: { border: string; paper: string; ink: string; radius: number };
  panelName?: string; label: string; closingLabel: string;
  portraits?: { name: string; intro: string; introBubble?: string; outro: string; outroBubble?: string };
};

export type TourProps = {
  video: string;                  // film du studio (raw.mp4) dans public/
  timeline: Timeline;             // journal du studio (studio_record.mjs)
  camera: { keyframes: Key[] };   // plan de caméra (studio_camera.py)
  look: Look;                     // habillage du style du bon (styles/<nom>/kit.json)
  opening: { title: string; subtitle?: string };
  closing: { lines: string[] };   // ce qu'il faut retenir, 2 à 4 phrases courtes
  introSeconds?: number;          // ouverture, avant le tour (4 s par défaut)
  outroSeconds?: number;          // fermeture, après le tour (5 s par défaut)
  audio?: string;                 // voix off dans public/, sur l'horloge du film (ouverture comprise)
  captions?: Caption[];           // sous-titres, sur l'horloge du film
  padding?: number;               // marge autour de la fenêtre, en part de la largeur
};

const seconds = (p: TourProps) => ({ intro: p.introSeconds ?? 4, outro: p.outroSeconds ?? 5 });

// Durée = ouverture + tournage (une image du film = une image du journal) + fermeture.
export const tourMetadata: CalculateMetadataFunction<TourProps> = ({ props }) => {
  const s = seconds(props), fps = props.timeline.fps;
  return { durationInFrames: Math.round(s.intro * fps) + Math.max(1, props.timeline.frames.length) + Math.round(s.outro * fps), fps };
};

function cameraAt(keys: Key[], f: number): Key {
  if (f <= keys[0].frame) return keys[0];
  for (let i = 0; i + 1 < keys.length; i++) {
    const a = keys[i], b = keys[i + 1];
    if (f <= b.frame) {
      const u = interpolate(f, [a.frame, b.frame], [0, 1], { easing: Easing.inOut(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
      return { frame: f, scale: a.scale + (b.scale - a.scale) * u, x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u };
    }
  }
  return keys[keys.length - 1];
}

const Arrow: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" style={{ overflow: "visible", filter: "drop-shadow(0 3px 6px rgba(0,0,0,.35))" }}>
    <path d="M4 2 L4 26 L10.5 20 L15 30 L19.5 28 L15 18.5 L24 18.5 Z" fill="#111" stroke="#fff" strokeWidth={2} strokeLinejoin="round" />
  </svg>
);

// Fond du style : halo de la charte, ou grille et sol du bureau pixel.
const Backdrop: React.FC<{ look: Look; W: number; H: number }> = ({ look, W, H }) => {
  const u = W / 1920;
  if (look.frame !== "pixel") return <AbsoluteFill style={{ background: "radial-gradient(120% 90% at 50% 0%, " + (look.halo ?? look.window) + " 0%, " + look.background + " 62%)" }} />;
  const step = 48 * u, line = Math.max(2, Math.round(2 * u));
  const grid = look.grid ?? look.accent, op = look.gridOpacity ?? 0.035;
  return (
    <AbsoluteFill style={{ background: look.background }}>
      <AbsoluteFill style={{ opacity: op, backgroundImage: "linear-gradient(" + grid + " " + line + "px, transparent " + line + "px), linear-gradient(90deg, " + grid + " " + line + "px, transparent " + line + "px)", backgroundSize: step + "px " + step + "px" }} />
      {look.floor && <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 132 * u * (H / W) * (1920 / 1080), background: look.floor, borderTop: 8 * u + "px solid rgba(255,255,255,.08)" }} />}
    </AbsoluteFill>
  );
};

// Étiquette du style (TUTORIEL, À RETENIR) : capsule de la charte ou plaque pixel.
const Label: React.FC<{ look: Look; text: string; u: number }> = ({ look, text, u }) => (
  <div style={{ display: "inline-block", padding: (look.frame === "pixel" ? 10 : 12) * u + "px " + 22 * u + "px", background: look.accent, color: look.onAccent ?? "#08110E",
    borderRadius: look.frame === "pixel" ? 0 : 999, fontWeight: 700, fontSize: 26 * u, letterSpacing: 6 * u,
    boxShadow: look.frame === "pixel" ? "0 0 0 " + 4 * u + "px " + (look.bezel?.outline ?? "#000") + ", " + 6 * u + "px " + 6 * u + "px 0 rgba(0,0,0,.45)" : "none" }}>{text}</div>
);

// Portrait « VOUS » en boîte de dialogue, avec sa bulle qui apparaît.
const Portrait: React.FC<{ look: Look; face: string; bubble?: string; u: number; at: number; f: number; fps: number }> = ({ look, face, bubble, u, at, f, fps }) => {
  if (!look.portraits) return null;
  const pop = spring({ frame: f - at, fps, config: { damping: 12 } });
  const b = spring({ frame: f - at - Math.round(0.5 * fps), fps, config: { damping: 10 } });
  return (
    <div style={{ position: "relative", width: 240 * u, transform: "scale(" + pop + ")", transformOrigin: "50% 100%" }}>
      <div style={{ background: look.dialog.border, padding: 6 * u }}>
        <div style={{ background: look.dialog.paper, padding: 8 * u }}>
          <div style={{ background: "#CFE8D9", width: 212 * u, height: 212 * u, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Img src={staticFile("style/" + face)} style={{ width: 192 * u, height: 192 * u, imageRendering: "pixelated" }} />
          </div>
          <div style={{ background: look.panelName ?? "#1D3A30", color: look.dialog.paper, marginTop: 10 * u, height: 56 * u, display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 600, fontSize: 26 * u, letterSpacing: 4 * u }}>{look.portraits.name}</div>
        </div>
      </div>
      {bubble && <Img src={staticFile("style/" + bubble)} style={{ position: "absolute", right: -30 * u, top: -100 * u, width: 90 * u, height: 90 * u, imageRendering: "pixelated", transform: "scale(" + b + ")" }} />}
    </div>
  );
};

// Cadre de la fenêtre filmée : fenêtre arrondie de la charte, ou écran de console pixel (anneaux crantés).
const Frame: React.FC<{ look: Look; x: number; y: number; w: number; h: number; u: number; children: React.ReactNode }> = ({ look, x, y, w, h, u, children }) => {
  if (look.frame !== "pixel" || !look.bezel) {
    return (
      <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 28 * u, overflow: "hidden", background: look.window,
        boxShadow: "0 " + 40 * u + "px " + 120 * u + "px rgba(0,0,0,.18), 0 0 0 " + 2 * u + "px rgba(0,0,0,.06)" }}>{children}</div>
    );
  }
  const b = look.bezel, ring = 6 * u, body = 26 * u;
  const notch = (n: number) => "polygon(" + n + "px 0, calc(100% - " + n + "px) 0, calc(100% - " + n + "px) " + n + "px, 100% " + n + "px, 100% calc(100% - " + n + "px), calc(100% - " + n + "px) calc(100% - " + n + "px), calc(100% - " + n + "px) 100%, " + n + "px 100%, " + n + "px calc(100% - " + n + "px), 0 calc(100% - " + n + "px), 0 " + n + "px, " + n + "px " + n + "px)";
  const o = ring + body + ring * 2;
  return (
    <div style={{ position: "absolute", left: x - o, top: y - o, width: w + 2 * o, height: h + 2 * o, background: b.outline, clipPath: notch(14 * u), filter: "drop-shadow(0 " + 18 * u + "px 0 rgba(0,0,0,.35))" }}>
      <div style={{ position: "absolute", inset: ring, background: b.body, clipPath: notch(12 * u), boxShadow: "inset " + 6 * u + "px " + 6 * u + "px 0 " + b.light + ", inset -" + 8 * u + "px -" + 10 * u + "px 0 " + b.shade }} />
      <div style={{ position: "absolute", left: ring + body, top: ring + body, width: w + 2 * ring, height: h + 2 * ring, background: b.outline }} />
      <div style={{ position: "absolute", left: ring * 2 + body - 3 * u, top: ring * 2 + body - 3 * u, width: w + 6 * u, height: h + 6 * u, background: b.screen }} />
      <div style={{ position: "absolute", left: o, top: o, width: w, height: h, overflow: "hidden", background: look.window }}>{children}</div>
    </div>
  );
};

export const InterfaceTour: React.FC<TourProps> = (props) => {
  const { video, timeline, camera, look, opening, closing, audio, captions = [], padding } = props;
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const W = timeline.width, H = timeline.height, zoom = timeline.zoom, u = W / 1920;
  const s = seconds(props), introF = Math.round(s.intro * fps), tourF = Math.max(1, timeline.frames.length), outroAt = introF + tourF;
  const pad = Math.round(W * (padding ?? (look.frame === "pixel" ? 0.075 : 0.05))), winW = W - 2 * pad, k = winW / W, winH = Math.round(H * k);
  const top = Math.round((H - winH) / 2) - (look.frame === "pixel" ? Math.round(24 * u) : 0);
  // Le tour entre en grandissant à la fin de l'ouverture et sort de même au début de la fermeture.
  const enter = interpolate(f, [introF - Math.round(0.6 * fps), introF], [0, 1], { easing: Easing.out(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const leave = interpolate(f, [outroAt, outroAt + Math.round(0.6 * fps)], [0, 1], { easing: Easing.in(Easing.cubic), extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tourScale = 0.86 + 0.14 * enter - 0.14 * leave, tourOpacity = Math.min(enter, 1 - leave);
  const tf = Math.min(Math.max(f - introF, 0), tourF - 1);
  const cam = cameraAt(camera.keyframes, tf);
  const toWin = (x: number, y: number) => ({ x: ((x - cam.x) * cam.scale + W / 2) * k, y: ((y - cam.y) * cam.scale + H / 2) * k });
  const raw = timeline.frames[tf].cursor;
  const cur = toWin(raw.x * zoom, raw.y * zoom);
  const cursorSize = 46 * zoom * k * (1 + (cam.scale - 1) * 0.45) * (raw.scale ?? 1);
  const ripples = timeline.events.filter((e) => e.type === "click").map((e) => Math.round((e.timeMs / 1000) * timeline.fps)).filter((st) => tf >= st && tf < st + 30);
  const caption = captions.find((x) => f >= (x.startMs / 1000) * fps && f < (x.endMs / 1000) * fps);
  const title = opening.title, typed = Math.min(title.length, Math.floor(interpolate(f, [Math.round(0.35 * fps), Math.round(1.6 * fps)], [0, title.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  const introOut = interpolate(f, [introF - Math.round(0.7 * fps), introF - Math.round(0.1 * fps)], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const outroIn = interpolate(f, [outroAt + Math.round(0.3 * fps), outroAt + Math.round(0.9 * fps)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fade = interpolate(f, [durationInFrames - Math.round(0.5 * fps), durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ fontFamily, opacity: fade }}>
      <Backdrop look={look} W={W} H={H} />

      {f < introF && (
        <AbsoluteFill style={{ opacity: introOut, padding: 180 * u + "px " + 200 * u + "px", display: "flex", flexDirection: "row", alignItems: "center", gap: 120 * u }}>
          <div style={{ flex: 1 }}>
            <Label look={look} text={look.label} u={u} />
            <div style={{ marginTop: 48 * u, color: look.frame === "pixel" ? look.ink : look.ink, fontSize: 112 * u, fontWeight: 700, lineHeight: 1.08, minHeight: 250 * u }}>
              {title.slice(0, typed)}<span style={{ opacity: f % fps < fps / 2 ? 1 : 0, color: look.accent }}>{typed < title.length || look.frame === "pixel" ? "▌" : ""}</span>
            </div>
            {opening.subtitle && <div style={{ marginTop: 24 * u, color: look.muted, fontSize: 44 * u, fontWeight: 500, opacity: interpolate(f, [Math.round(1.6 * fps), Math.round(2.1 * fps)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{opening.subtitle}</div>}
          </div>
          {look.portraits && <Portrait look={look} face={look.portraits.intro} bubble={look.portraits.introBubble} u={u * 1.4} at={Math.round(0.9 * fps)} f={f} fps={fps} />}
        </AbsoluteFill>
      )}

      {f >= introF - Math.round(0.6 * fps) && f < outroAt + Math.round(0.6 * fps) && (
        <AbsoluteFill style={{ opacity: tourOpacity, transform: "scale(" + tourScale + ")" }}>
          <Frame look={look} x={pad} y={top} w={winW} h={winH} u={u}>
            <div style={{ position: "absolute", width: W, height: H, left: 0, top: 0, transformOrigin: "0 0",
              transform: "scale(" + k + ") translate(" + (W / 2 - cam.x * cam.scale) + "px," + (H / 2 - cam.y * cam.scale) + "px) scale(" + cam.scale + ")" }}>
              {/* Pendant que la fenêtre entre et sort, elle montre la première et la dernière image du tournage, figées :
                  jamais une fenêtre vide (écran blanc avant la fermeture). */}
              {f < introF ? (
                <Freeze frame={0}><OffthreadVideo src={staticFile(video)} muted style={{ width: W, height: H }} /></Freeze>
              ) : f >= outroAt ? (
                <Freeze frame={tourF - 1}><OffthreadVideo src={staticFile(video)} muted style={{ width: W, height: H }} /></Freeze>
              ) : (
                <Sequence from={introF} durationInFrames={tourF} layout="none">
                  <OffthreadVideo src={staticFile(video)} muted style={{ width: W, height: H }} />
                </Sequence>
              )}
            </div>
            {ripples.map((st) => {
              const at = timeline.frames[Math.min(st, tourF - 1)].cursor, p = toWin(at.x * zoom, at.y * zoom);
              const t = (tf - st) / 30, r = (18 + 70 * Easing.out(Easing.cubic)(t)) * zoom * k * cam.scale;
              return <div key={st} style={{ position: "absolute", left: p.x - r, top: p.y - r, width: 2 * r, height: 2 * r, borderRadius: look.frame === "pixel" ? 0 : "50%",
                border: 4 * zoom * k + "px solid " + look.accent, opacity: 0.8 * (1 - t) }} />;
            })}
            <div style={{ position: "absolute", left: cur.x - cursorSize * 0.125, top: cur.y - cursorSize * 0.06 }}><Arrow size={cursorSize} /></div>
          </Frame>
        </AbsoluteFill>
      )}

      {f >= outroAt && (
        <AbsoluteFill style={{ opacity: outroIn, padding: 180 * u + "px " + 200 * u + "px", display: "flex", flexDirection: "row", alignItems: "center", gap: 120 * u }}>
          <div style={{ flex: 1 }}>
            <Label look={look} text={look.closingLabel} u={u} />
            <div style={{ marginTop: 52 * u, display: "flex", flexDirection: "column", gap: 30 * u }}>
              {closing.lines.map((line, i) => {
                const show = interpolate(f, [outroAt + Math.round((0.6 + i * 0.45) * fps), outroAt + Math.round((0.95 + i * 0.45) * fps)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
                return (
                  <div key={i} style={{ display: "flex", gap: 28 * u, alignItems: "baseline", opacity: show, transform: "translateX(" + (1 - show) * 40 * u + "px)" }}>
                    <span style={{ width: 22 * u, height: 22 * u, flex: "0 0 auto", background: i % 2 ? (look.accent2 ?? look.accent) : look.accent, borderRadius: look.frame === "pixel" ? 0 : 999 }} />
                    <span style={{ color: look.ink, fontSize: 60 * u, fontWeight: 600, lineHeight: 1.2 }}>{line}</span>
                  </div>
                );
              })}
            </div>
          </div>
          {look.portraits && <Portrait look={look} face={look.portraits.outro} bubble={look.portraits.outroBubble} u={u * 1.4} at={outroAt + Math.round(0.4 * fps)} f={f} fps={fps} />}
        </AbsoluteFill>
      )}

      {caption && (
        <div style={{ position: "absolute", left: 0, right: 0, bottom: (look.frame === "pixel" ? 40 : 70) * u, display: "flex", justifyContent: "center" }}>
          <div style={{ maxWidth: W * 0.72, padding: 22 * u + "px " + 40 * u + "px", borderRadius: look.dialog.radius * u, background: look.dialog.paper, color: look.dialog.ink,
            border: (look.frame === "pixel" ? 6 : 0) * u + "px solid " + look.dialog.border, boxShadow: look.frame === "pixel" ? 8 * u + "px " + 8 * u + "px 0 rgba(0,0,0,.45)" : "0 10px 40px rgba(0,0,0,.25)",
            fontSize: 58 * u, fontWeight: 600, lineHeight: 1.25, textAlign: "center" }}>{caption.text}</div>
        </div>
      )}
      {audio && <Audio src={staticFile(audio)} />}
    </AbsoluteFill>
  );
};

