import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import storyboard from "./storyboard.json";
import audio from "./audio.json";

/* Vidéo de l'essentiel d'un appel d'offres (skill ao-essentiel-motion) : rendu du storyboard.json préparé par Oscar,
   motion designer de l'équipe Appels d'offres de Rossini Sales Suite. Chaque capture garde sa source à l'écran ; un
   agent nommé apparaît avec son portrait ; « Qui vérifie quoi » vient du pli de réponse. */

export const { fontFamily } = loadFont("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin", "latin-ext"] });

type Word = { t: string; s: number; e: number };
type Cue = { text: string; start: number; end: number };
type Voice = { file: string; durationSec: number; words: Word[]; cues: Cue[] };
type CamKey = { at: string | null; s: number; x: number; y: number };
type Hl = { box: number[]; at: string | null };
type Source = { type: string; explication: string; nom?: string; page?: number; citation?: string; document?: string; piece_pli?: string };
type Shot = { capture: string; file: string; at: string | null; cam: CamKey[]; hl: Hl[] };
type Capture = { id: string; fichier: string; genre: string; titre: string; largeur: number; hauteur: number; boite: number[] | null; agent: string; source: Source };
type Ligne = { personne: string; personne_id: string; fonction: string; pieces: { numero: string; nom: string; statut: string; agents: string[] }[] };
type Scene = { id: string; chapitre: string; titre: string; voix: string; texte_ecran: string[]; agents: string[]; personnes: string[]; shots: Shot[]; verification?: Ligne[] };
type Agent = { id: string; prenom: string; fonction: string; couleur: string; file: string | null };
type Personne = { id: string; nom: string; fonction: string; file: string | null };

const SB = storyboard as unknown as {
  fps: number; width: number; height: number; leadSec: number; gapSec: number; tailSec: number;
  dossier: { titre: string; acheteur: string }; titre: string; accroche: string; steps: string[];
  scenes: Scene[]; captures: Capture[]; agents: Agent[]; personnes: Personne[];
  auteur: { prenom: string }; charte: { couleurs: Record<string, string> };
};
const A = audio as unknown as { estime?: boolean; voice: Record<string, Voice> };
const V = A.voice;
export const FPS = SB.fps;
const K = SB.charte.couleurs;
const C = { bg: K.fond, ink: K.encre, text: K.texte, sub: K.gris, line: K.gris_clair, red: K.rouge, card: K.blanc, hl: K.surligneur };
const XFADE = 0.4;
const CAPS = new Map(SB.captures.map((c) => [c.id, c]));
const AGENTS = new Map(SB.agents.map((a) => [a.id, a]));
const GENS = new Map(SB.personnes.map((p) => [p.id, p]));

/* ---------- temps ---------- */
const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fadeIn = (t: number, t0: number, d = 0.4) => interpolate(t, [t0, t0 + d], [0, 1], clamp);
const norm = (t: string) => t.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const toks = (t: string) => norm(t).match(/[a-z0-9]+/g) ?? [];

export const layout = (() => {
  let t = 0;
  return SB.scenes.map((s, i) => {
    const v = V[s.id];
    if (!v) throw new Error("Voix absente pour la scène " + s.id + " : lancez voice_scenes.py (ou paquet.py estimer pour une maquette).");
    const lead = i === 0 ? SB.leadSec : 0.15;
    const tail = i === SB.scenes.length - 1 ? SB.tailSec : SB.gapSec;
    const r = { scene: s, start: t, lead, dur: lead + v.durationSec + tail };
    t += r.dur;
    return r;
  });
})();
export const totalFrames = () => Math.round(layout.reduce((a, l) => a + l.dur, 0) * FPS);

function wordAt(sceneId: string, lead: number, key: string | null | undefined): number {
  if (!key) return 0;
  const want = toks(key);
  const words = V[sceneId].words;
  for (let i = 0; i < words.length; i++) {
    if (want.every((w, j) => words[i + j] && toks(words[i + j].t).join("").startsWith(w))) return lead + words[i].s;
  }
  throw new Error("Mot déclencheur introuvable dans la voix : " + sceneId + " / " + key);
}
type Ctx = { t: number; at: (k: string | null | undefined) => number; dur: number; scene: Scene; lead: number };

/* ---------- pièces communes ---------- */
const Logo: React.FC<{ h: number }> = ({ h }) => <Img src={staticFile("brand/logo.png")} style={{ height: h, width: "auto", display: "block" }} />;

const initiales = (nom: string) => nom.split(/\s+/).filter(Boolean).slice(0, 2).map((m) => m[0]!.toUpperCase()).join("");
const Portrait: React.FC<{ file: string | null; nom: string; couleur?: string; size: number }> = ({ file, nom, couleur, size }) =>
  file ? <Img src={staticFile(file)} style={{ width: size, height: size, borderRadius: size / 2, objectFit: "cover", display: "block", flex: "none", background: C.card, boxShadow: "0 4px 14px rgba(0,0,0,.12)" }} />
    : <div style={{ width: size, height: size, borderRadius: size / 2, flex: "none", display: "grid", placeItems: "center", background: couleur || C.ink, color: C.card, fontWeight: 800, fontSize: size * 0.38 }}>{initiales(nom)}</div>;

const AgentChip: React.FC<{ id: string; o: number; size?: number }> = ({ id, o, size = 76 }) => {
  const a = AGENTS.get(id);
  if (!a) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: o, transform: "translateY(" + (1 - o) * 16 + "px)" }}>
      <Portrait file={a.file} nom={a.prenom} couleur={a.couleur} size={size} />
      <div><div style={{ fontSize: 32, fontWeight: 800, color: C.ink }}>{a.prenom}</div><div style={{ fontSize: 22, fontWeight: 500, color: C.sub }}>{a.fonction}</div></div>
    </div>
  );
};

/* ---------- titre et conclusion ---------- */
const TitleCard: React.FC<{ ctx: Ctx; first: boolean }> = ({ ctx, first }) => {
  const { t, scene } = ctx;
  const o = fadeIn(t, 0, 0.6);
  const bar = ease((t - 0.2) / 0.9);
  const lignes = scene.texte_ecran;
  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", paddingLeft: 190, paddingRight: 190 }}>
      <div style={{ opacity: o, transform: "translateY(" + (1 - o) * 26 + "px)" }}>
        <Logo h={first ? 96 : 72} />
        <div style={{ height: 8, width: 220 * bar, background: C.red, borderRadius: 4, margin: "36px 0 30px" }} />
        <div style={{ fontSize: first ? 84 : 72, fontWeight: 800, color: C.ink, letterSpacing: -2, lineHeight: 1.06, maxWidth: 1500 }}>{first ? SB.titre : scene.titre}</div>
        <div style={{ fontSize: 36, fontWeight: 500, color: C.sub, marginTop: 22, maxWidth: 1400 }}>{first ? [SB.dossier.titre, SB.dossier.acheteur].filter(Boolean).join(" · ") : SB.dossier.titre}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginTop: 44 }}>
          {lignes.map((l, i) => { const oi = fadeIn(t, 0.9 + i * 0.5, 0.45); return <div key={i} style={{ fontSize: 30, fontWeight: 700, color: C.ink, background: C.card, borderRadius: 14, padding: "12px 22px", opacity: oi, boxShadow: "0 8px 24px rgba(0,0,0,.06)" }}>{l}</div>; })}
        </div>
        {scene.agents.length ? <div style={{ display: "flex", gap: 40, marginTop: 48 }}>{scene.agents.map((id, i) => <AgentChip key={id} id={id} o={fadeIn(t, 1.4 + i * 0.4)} size={64} />)}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

/* ---------- page capturée (DCE ou livrable d'agent) ---------- */
const SX = 150, SY = 150, SW = 1000, SH = 820;
function camAt(t: number, keys: { t: number; s: number; x: number; y: number }[]) {
  let cur = { s: 1, x: 0.5, y: 0.5 };
  for (const k of keys) {
    if (t < k.t) break;
    const p = ease((t - k.t) / 1.0);
    cur = { s: cur.s + (k.s - cur.s) * p, x: cur.x + (k.x - cur.x) * p, y: cur.y + (k.y - cur.y) * p };
  }
  return cur;
}
const placer = (taille: number, cadre: number, centre: number) => (taille <= cadre ? (cadre - taille) / 2 : Math.min(0, Math.max(cadre - taille, cadre / 2 - centre * taille)));

const PageView: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { t, at, dur, scene } = ctx;
  const shots = scene.shots.map((sh, i) => ({ sh, cap: CAPS.get(sh.capture)!, t0: i === 0 ? 0 : at(sh.at) }));
  const active = shots.reduce((a, x, i) => (t >= x.t0 ? i : a), 0);
  const enter = spring({ frame: Math.round(t * FPS), fps: FPS, config: { damping: 200 }, durationInFrames: 30 });
  const cur = shots[active].cap;
  const src = cur.source;
  const legende = src.type === "piece_dce" ? [src.nom, src.page ? "page " + src.page : ""].filter(Boolean).join(" · ") : src.document || cur.titre;
  const citation = src.type === "piece_dce" && src.citation ? "« " + src.citation + " »" : src.piece_pli ? "Pièce " + src.piece_pli + " du pli" : "";
  const producteurs = Array.from(new Set([...shots.map((x) => x.cap.agent).filter(Boolean), ...scene.agents]));
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <div style={{ position: "absolute", left: SX, top: SY, width: SW, height: SH, borderRadius: 18, overflow: "hidden", background: C.line, boxShadow: "0 24px 70px rgba(20,24,32,.22)", opacity: enter, transform: "scale(" + (0.96 + 0.04 * enter) + ")" }}>
        {shots.map(({ sh, cap, t0 }, i) => {
          const t1 = i + 1 < shots.length ? shots[i + 1].t0 : dur + 1;
          if (t < t0 - 0.01 || t > t1 + 0.5) return null;
          const o = i === 0 ? 1 : fadeIn(t, t0, 0.45);
          const k = Math.min(SW / cap.largeur, SH / cap.hauteur);
          const c = camAt(t, sh.cam.map((x) => ({ t: x.at ? at(x.at) : t0, s: x.s, x: x.x, y: x.y })));
          const pw = cap.largeur * k * c.s, ph = cap.hauteur * k * c.s;
          const tx = placer(pw, SW, c.x), ty = placer(ph, SH, c.y);
          return (
            <div key={i} style={{ position: "absolute", inset: 0, opacity: o }}>
              <Img src={staticFile(sh.file)} style={{ position: "absolute", left: tx, top: ty, width: pw, height: ph, display: "block", background: C.card }} />
              {sh.hl.map((h, j) => {
                const ho = Math.min(fadeIn(t, h.at ? at(h.at) : t0 + 0.6, 0.35), interpolate(t, [t1 - 0.3, t1], [1, 0], clamp));
                if (ho <= 0) return null;
                const [x0, y0, x1, y1] = h.box, s = k * c.s, pad = 10, grow = (1 - ho) * 14;
                return <div key={j} style={{ position: "absolute", left: tx + x0 * s - pad - grow, top: ty + y0 * s - pad - grow, width: (x1 - x0) * s + 2 * (pad + grow), height: (y1 - y0) * s + 2 * (pad + grow), border: "5px solid " + C.red, borderRadius: 12, opacity: ho, boxShadow: "0 0 0 9999px rgba(20,24,32," + 0.22 * ho + ")" }} />;
              })}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: SX, top: SY + SH + 18, width: SW, display: "flex", alignItems: "center", gap: 14, opacity: enter }}>
        <span style={{ background: C.ink, color: C.card, borderRadius: 8, padding: "6px 14px", fontSize: 21, fontWeight: 700, flex: "none" }}>Source</span>
        <span style={{ fontSize: 21, color: C.text, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{legende}{citation ? <span style={{ fontWeight: 500, color: C.sub }}>{"  " + citation}</span> : null}</span>
      </div>
      <div style={{ position: "absolute", left: SX + SW + 70, top: SY + 10, width: 1920 - (SX + SW + 70) - 120 }}>
        <div style={{ fontSize: 52, fontWeight: 800, color: C.ink, letterSpacing: -1, lineHeight: 1.08, opacity: fadeIn(t, 0.1, 0.5) }}>{scene.titre}</div>
        <div style={{ height: 6, width: 120 * ease(t / 0.8), background: C.red, borderRadius: 3, margin: "26px 0 30px" }} />
        {scene.texte_ecran.map((l, i) => { const oi = fadeIn(t, 0.7 + i * 0.7, 0.45); return <div key={i} style={{ fontSize: 34, fontWeight: 700, color: C.text, lineHeight: 1.25, marginBottom: 20, opacity: oi, transform: "translateX(" + (1 - oi) * -20 + "px)" }}>{l}</div>; })}
        <div style={{ display: "flex", flexDirection: "column", gap: 22, marginTop: 34 }}>
          {producteurs.map((id, i) => <AgentChip key={id} id={id} o={fadeIn(t, 1.2 + i * 0.5)} />)}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- qui vérifie quoi ---------- */
const Verification: React.FC<{ ctx: Ctx }> = ({ ctx }) => {
  const { t, scene } = ctx;
  const lignes = scene.verification ?? [];
  const deux = lignes.length > 3;
  return (
    <AbsoluteFill style={{ background: C.bg, padding: "150px 150px 0" }}>
      <div style={{ fontSize: 58, fontWeight: 800, color: C.ink, letterSpacing: -1, marginBottom: 38, opacity: fadeIn(t, 0, 0.5) }}>{scene.titre}</div>
      <div style={{ display: "grid", gridTemplateColumns: deux ? "1fr 1fr" : "1fr", gap: "22px 34px" }}>
        {lignes.map((l, i) => {
          const o = fadeIn(t, 0.6 + i * 0.6, 0.45);
          const p = GENS.get(l.personne_id);
          const visibles = l.pieces.slice(0, deux ? 3 : 5), reste = l.pieces.length - visibles.length;
          const ags = Array.from(new Set(l.pieces.flatMap((x) => x.agents))).slice(0, 6);
          return (
            <div key={i} style={{ background: C.card, borderRadius: 22, padding: "22px 26px", boxShadow: "0 12px 34px rgba(20,24,32,.08)", opacity: o, transform: "translateY(" + (1 - o) * 20 + "px)", display: "flex", gap: 22 }}>
              <Portrait file={p?.file ?? null} nom={l.personne} size={78} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 32, fontWeight: 800, color: C.ink }}>{l.personne}</span>
                  <span style={{ fontSize: 22, fontWeight: 700, color: C.card, background: C.red, borderRadius: 99, padding: "3px 14px" }}>{l.pieces.length} {l.pieces.length > 1 ? "pièces à valider" : "pièce à valider"}</span>
                </div>
                <div style={{ fontSize: 21, color: C.sub, fontWeight: 600, margin: "4px 0 10px" }}>{l.fonction}</div>
                {visibles.map((x, j) => <div key={j} style={{ fontSize: 22, color: C.text, lineHeight: 1.35, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}><b>{x.numero}</b> {x.nom} <span style={{ color: C.sub }}>· {x.statut.toLowerCase()}</span></div>)}
                {reste > 0 ? <div style={{ fontSize: 21, color: C.sub, marginTop: 4 }}>et {reste} autre{reste > 1 ? "s" : ""}</div> : null}
                {ags.length ? <div style={{ display: "flex", gap: 10, marginTop: 12, alignItems: "center" }}>{ags.map((id) => { const a = AGENTS.get(id); return a ? <div key={id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 19, color: C.sub, fontWeight: 600 }}><Portrait file={a.file} nom={a.prenom} couleur={a.couleur} size={34} />{a.prenom}</div> : null; })}</div> : null}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 150, bottom: 150, fontSize: 21, color: C.sub, fontWeight: 600, opacity: fadeIn(t, 1, 0.5) }}>Source : pli de réponse du dossier, relecteur et statut de chaque pièce</div>
    </AbsoluteFill>
  );
};

/* ---------- habillage ---------- */
const Header: React.FC<{ scene: Scene; t: number; idx: number }> = ({ scene, t, idx }) => {
  if (idx === 0) return null;
  const n = SB.steps.indexOf(scene.chapitre);
  return (
    <div style={{ position: "absolute", left: 150, right: 150, top: 46, height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", opacity: fadeIn(t, 0, 0.3) }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <Logo h={42} />
        <div style={{ width: 2, height: 34, background: C.line }} />
        <span style={{ fontSize: 25, fontWeight: 800, color: C.red }}>{String(n + 1).padStart(2, "0")}</span>
        <span style={{ fontSize: 25, fontWeight: 700, color: C.ink }}>{scene.chapitre}</span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>{SB.steps.map((s, i) => <div key={s} style={{ width: 34, height: 6, borderRadius: 3, background: i <= n ? C.red : C.line }} />)}</div>
    </div>
  );
};

const Subtitles: React.FC<{ cues: Cue[]; t: number }> = ({ cues, t }) => {
  const c = cues.find((x) => t >= x.start && t < x.end);
  if (!c) return null;
  const o = Math.min(fadeIn(t, c.start, 0.15), interpolate(t, [c.end - 0.12, c.end], [1, 0], clamp));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 40, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ maxWidth: 1500, background: "rgba(29,29,27,.88)", color: C.card, fontSize: 32, fontWeight: 600, lineHeight: 1.3, padding: "12px 26px", borderRadius: 12, textAlign: "center" }}>{c.text}</div>
    </div>
  );
};

// Voix estimée (paquet.py estimer) : chaque image le dit, pour qu'aucune maquette ne parte comme une vidéo finie.
const Maquette: React.FC = () => (
  <div style={{ position: "absolute", right: 24, bottom: 24, background: C.red, color: C.card, fontSize: 24, fontWeight: 800, padding: "8px 16px", borderRadius: 10 }}>MAQUETTE · voix estimée, pas de son</div>
);

const SceneView: React.FC<{ idx: number }> = ({ idx }) => {
  const frame = useCurrentFrame();
  const L = layout[idx];
  const t = frame / FPS;
  const scene = L.scene;
  const ctx: Ctx = { t, dur: L.dur, scene, lead: L.lead, at: (k) => (k ? wordAt(scene.id, L.lead, k) : 0) };
  let body: React.ReactNode;
  if (scene.verification) body = <Verification ctx={ctx} />;
  else if (scene.shots.length) body = <PageView ctx={ctx} />;
  else body = <TitleCard ctx={ctx} first={idx === 0} />;
  const fadeOut = idx === layout.length - 1 ? interpolate(t, [L.dur - 0.6, L.dur], [1, 0], clamp) : 1;
  const fadeInScene = idx === 0 ? 1 : interpolate(t, [0, XFADE], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ fontFamily, opacity: fadeOut * fadeInScene }}>
      {body}
      <Header scene={scene} t={t} idx={idx} />
      <Subtitles cues={(V[scene.id].cues ?? []).map((c) => ({ ...c, start: c.start + L.lead, end: c.end + L.lead }))} t={t} />
      {A.estime ? <Maquette /> : <Sequence from={Math.round(L.lead * FPS)}><Audio src={staticFile(V[scene.id].file)} /></Sequence>}
    </AbsoluteFill>
  );
};

export const EssentielVideo: React.FC = () => {
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

export const meta = { fps: SB.fps, width: SB.width, height: SB.height };

