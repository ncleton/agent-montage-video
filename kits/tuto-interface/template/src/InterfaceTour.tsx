import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, interpolate, Easing, staticFile, useCurrentFrame, type CalculateMetadataFunction } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["500", "600"], subsets: ["latin", "latin-ext"] });

type Cursor = { x: number; y: number; scale?: number };
type Timeline = { fps: number; width: number; height: number; zoom: number; frames: { cursor: Cursor }[]; events: { type: "click" | "key"; timeMs: number }[] };
type Key = { frame: number; scale: number; x: number; y: number };
export type Caption = { startMs: number; endMs: number; text: string };
export type TourProps = {
  video: string;                  // film du studio (raw.mp4) dans public/
  timeline: Timeline;             // journal du studio (studio_record.mjs)
  camera: { keyframes: Key[] };   // plan de caméra (studio_camera.py)
  theme?: "light" | "dark";
  audio?: string;                 // voix off dans public/, calée sur les repères du journal
  captions?: Caption[];           // sous-titres incrustés
  accent?: string;                // couleur principale de la charte (Administration › Charte graphique)
  padding?: number;               // marge autour de la fenêtre, en part de la largeur
};

// Durée = celle du tournage : le film et le journal ont le même nombre d'images.
export const tourMetadata: CalculateMetadataFunction<TourProps> = ({ props }) => ({
  durationInFrames: Math.max(1, props.timeline.frames.length),
  fps: props.timeline.fps,
});

const CHARTE = {
  light: { background: "#F0F0F2", halo: "#FFFFFF", ink: "#1D1D1B", accent: "#e3342f", window: "#FFFFFF" },
  dark: { background: "#0b0b0c", halo: "#1c1c1f", ink: "#F2F3F5", accent: "#FFFFFF", window: "#161618" },
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

// Flèche de curseur, dessinée nette à toutes les tailles.
const Arrow: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" style={{ overflow: "visible", filter: "drop-shadow(0 3px 6px rgba(0,0,0,.35))" }}>
    <path d="M4 2 L4 26 L10.5 20 L15 30 L19.5 28 L15 18.5 L24 18.5 Z" fill="#111" stroke="#fff" strokeWidth={2} strokeLinejoin="round" />
  </svg>
);

export const InterfaceTour: React.FC<TourProps> = ({ video, timeline, camera, theme = "light", audio, captions = [], accent, padding = 0.05 }) => {
  const f = useCurrentFrame();
  const c = { ...CHARTE[theme], ...(accent ? { accent } : {}) };
  const W = timeline.width, H = timeline.height, zoom = timeline.zoom;
  // La fenêtre occupe l'écran moins sa marge ; tout ce qui est filmé y est réduit de k.
  const pad = Math.round(W * padding), winW = W - 2 * pad, k = winW / W, winH = Math.round(H * k);
  const top = Math.round((H - winH) / 2);
  const cam = cameraAt(camera.keyframes, f);
  // Point filmé (pixels de la vidéo) -> point dans la fenêtre, caméra appliquée.
  const toWin = (x: number, y: number) => ({ x: ((x - cam.x) * cam.scale + W / 2) * k, y: ((y - cam.y) * cam.scale + H / 2) * k });
  const raw = timeline.frames[Math.min(f, timeline.frames.length - 1)].cursor;
  const cur = toWin(raw.x * zoom, raw.y * zoom);
  const cursorSize = 46 * zoom * k * (1 + (cam.scale - 1) * 0.45) * (raw.scale ?? 1);
  const ripples = timeline.events.filter((e) => e.type === "click").map((e) => Math.round((e.timeMs / 1000) * timeline.fps)).filter((s) => f >= s && f < s + 30);
  const caption = captions.find((x) => f >= (x.startMs / 1000) * timeline.fps && f < (x.endMs / 1000) * timeline.fps);
  const radius = 28 * zoom * k;
  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 90% at 50% 0%, " + c.halo + " 0%, " + c.background + " 62%)", fontFamily }}>
      <div style={{ position: "absolute", left: pad, top, width: winW, height: winH, borderRadius: radius, overflow: "hidden", background: c.window,
        boxShadow: "0 " + 40 * k + "px " + 120 * k + "px rgba(0,0,0," + (theme === "dark" ? 0.6 : 0.18) + "), 0 0 0 " + 2 * k + "px rgba(0,0,0,.06)" }}>
        <div style={{ position: "absolute", width: W, height: H, left: 0, top: 0, transformOrigin: "0 0",
          transform: "scale(" + k + ") translate(" + (W / 2 - cam.x * cam.scale) + "px," + (H / 2 - cam.y * cam.scale) + "px) scale(" + cam.scale + ")" }}>
          <OffthreadVideo src={staticFile(video)} muted style={{ width: W, height: H }} />
        </div>
        {ripples.map((s) => {
          const at = timeline.frames[Math.min(s, timeline.frames.length - 1)].cursor, p = toWin(at.x * zoom, at.y * zoom);
          const u = (f - s) / 30, r = (18 + 70 * Easing.out(Easing.cubic)(u)) * zoom * k * cam.scale;
          return <div key={s} style={{ position: "absolute", left: p.x - r, top: p.y - r, width: 2 * r, height: 2 * r, borderRadius: "50%",
            border: 4 * zoom * k + "px solid " + c.accent, opacity: 0.75 * (1 - u) }} />;
        })}
        <div style={{ position: "absolute", left: cur.x - cursorSize * 0.125, top: cur.y - cursorSize * 0.06 }}><Arrow size={cursorSize} /></div>
      </div>
      {caption && (
        <div style={{ position: "absolute", left: 0, right: 0, bottom: top + 70 * k, display: "flex", justifyContent: "center" }}>
          <div style={{ maxWidth: W * 0.7, padding: 22 * k + "px " + 40 * k + "px", borderRadius: 18 * k, background: "rgba(17,17,17,.82)",
            color: "#fff", fontSize: 62 * k, fontWeight: 600, lineHeight: 1.25, textAlign: "center" }}>{caption.text}</div>
        </div>
      )}
      {audio && <Audio src={staticFile(audio)} />}
    </AbsoluteFill>
  );
};
