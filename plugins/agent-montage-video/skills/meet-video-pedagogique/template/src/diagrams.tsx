import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, Ctx, Visual, clamp, ease, fadeIn } from "./theme";

type D = React.FC<{ ctx: Ctx; v: Visual }>;
const W = 1920, H = 1080;

const Title: React.FC<{ text: string; t: number }> = ({ text, t }) => (
  <div style={{ position: "absolute", left: 200, top: 150, fontSize: 54, fontWeight: 800, color: C.ink, letterSpacing: -1, opacity: fadeIn(t, 0, 0.5) }}>{text}</div>
);
const Label: React.FC<{ x: number; y: number; o: number; children: React.ReactNode; color?: string; size?: number; w?: number; align?: "left" | "center" | "right"; bold?: boolean }> = ({ x, y, o, children, color = C.ink, size = 34, w = 560, align = "center", bold = true }) => (
  <div style={{ position: "absolute", left: align === "center" ? x - w / 2 : align === "right" ? x - w : x, top: y, width: w, textAlign: align, fontSize: size, fontWeight: bold ? 700 : 500, color, opacity: o, transform: "translateY(" + (1 - o) * 14 + "px)", lineHeight: 1.2 }}>{children}</div>
);
const Pill: React.FC<{ x: number; y: number; o: number; children: React.ReactNode; bg?: string }> = ({ x, y, o, children, bg = C.red }) => (
  <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%,0) scale(" + (0.85 + 0.15 * o) + ")", opacity: o, background: bg, color: "#fff", fontWeight: 800, fontSize: 34, padding: "12px 26px", borderRadius: 40, whiteSpace: "nowrap" }}>{children}</div>
);
/** Arrow drawn progressively from (x1,y1) to (x2,y2). */
const Arrow: React.FC<{ x1: number; y1: number; x2: number; y2: number; p: number; color: string; w?: number; both?: boolean; dash?: boolean }> = ({ x1, y1, x2, y2, p, color, w = 8, both, dash }) => {
  if (p <= 0) return null;
  const x = x1 + (x2 - x1) * p, y = y1 + (y2 - y1) * p;
  const a = Math.atan2(y2 - y1, x2 - x1);
  const head = (hx: number, hy: number, ang: number) => {
    const s = w * 2.6;
    return <polygon points={hx + "," + hy + " " + (hx - s * Math.cos(ang - 0.45)) + "," + (hy - s * Math.sin(ang - 0.45)) + " " + (hx - s * Math.cos(ang + 0.45)) + "," + (hy - s * Math.sin(ang + 0.45))} fill={color} />;
  };
  return (
    <g>
      <line x1={x1} y1={y1} x2={x} y2={y} stroke={color} strokeWidth={w} strokeLinecap="round" strokeDasharray={dash ? "18 14" : undefined} />
      {head(x, y, a)}
      {both && p >= 1 ? head(x1, y1, a + Math.PI) : null}
    </g>
  );
};
const Svg: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg width={W} height={H} viewBox={"0 0 " + W + " " + H} style={{ position: "absolute", inset: 0 }}>{children}</svg>
);
const prog = (t: number, t0: number, d = 0.8) => interpolate(t, [t0, t0 + d], [0, 1], { ...clamp, easing: ease });

/* Car, building, pylon, charger icons drawn with simple shapes */
const Car: React.FC<{ x: number; y: number; s?: number; color?: string }> = ({ x, y, s = 1, color = C.grey }) => (
  <g transform={"translate(" + x + "," + y + ") scale(" + s + ")"}>
    <path d="M-150,20 L-130,-25 Q-115,-55 -80,-58 L70,-58 Q105,-55 125,-25 L150,20 Q160,30 150,45 L-150,45 Q-160,30 -150,20 Z" fill={color} />
    <path d="M-100,-28 L-80,-48 L-10,-48 L-10,-28 Z M5,-28 L5,-48 L65,-48 L95,-28 Z" fill="#cfd6df" />
    <circle cx={-90} cy={48} r={26} fill="#222" /><circle cx={90} cy={48} r={26} fill="#222" />
    <circle cx={-90} cy={48} r={10} fill="#999" /><circle cx={90} cy={48} r={10} fill="#999" />
  </g>
);
const Charger: React.FC<{ x: number; y: number; big?: boolean; label: string }> = ({ x, y, big, label }) => (
  <g transform={"translate(" + x + "," + y + ")"}>
    <rect x={big ? -70 : -45} y={big ? -230 : -170} width={big ? 140 : 90} height={big ? 230 : 170} rx={16} fill={C.ink} />
    <rect x={big ? -50 : -30} y={big ? -205 : -150} width={big ? 100 : 60} height={46} rx={8} fill="#2e3a4a" />
    <text x={0} y={big ? -173 : -118} textAnchor="middle" fontSize={26} fontWeight={800} fill="#fff">{label}</text>
  </g>
);
const Fan: React.FC<{ x: number; y: number; t: number; o: number }> = ({ x, y, t, o }) => (
  <g transform={"translate(" + x + "," + y + ") rotate(" + t * 420 + ")"} opacity={o}>
    {[0, 120, 240].map((r) => <ellipse key={r} cx={0} cy={-18} rx={10} ry={18} fill="#9fb3c8" transform={"rotate(" + r + ")"} />)}
    <circle r={6} fill="#fff" />
  </g>
);
const Battery: React.FC<{ x: number; y: number; level: number; w?: number }> = ({ x, y, level, w = 120 }) => (
  <g transform={"translate(" + x + "," + y + ")"}>
    <rect x={-w / 2} y={-30} width={w} height={60} rx={10} fill="#fff" stroke={C.ink} strokeWidth={5} />
    <rect x={w / 2} y={-12} width={10} height={24} rx={3} fill={C.ink} />
    <rect x={-w / 2 + 7} y={-23} width={(w - 14) * level} height={46} rx={5} fill={C.green} />
  </g>
);

/* ---------- 1. AC vs DC ---------- */
const AcDc: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tPoids = at("poids"), t16 = at("seize"), t32 = at("trente"), tVite = at("vite"), tFan = at("ventilateur"), tCont = at("continu");
  const dcO = fadeIn(t, tVite, 0.6);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Chargeur dans la voiture ou dans la borne ?" t={t} />
      <Svg>
        <rect x={150} y={270} width={780} height={620} rx={28} fill="#fff" />
        <rect x={990} y={270} width={780} height={620} rx={28} fill="#fff" opacity={dcO} />
        <Charger x={300} y={720} label="AC" />
        <Arrow x1={350} y1={640} x2={470} y2={640} p={prog(t, 0.3)} color={C.blue} w={7} />
        <Car x={640} y={680} s={1.15} />
        <g opacity={fadeIn(t, t16)}>
          <rect x={560} y={520} width={70} height={52} rx={8} fill={C.amber} />
          <text x={595} y={555} textAnchor="middle" fontSize={22} fontWeight={800} fill="#fff">16 A</text>
        </g>
        <g opacity={fadeIn(t, t32)}>
          <rect x={650} y={500} width={110} height={72} rx={8} fill={C.red} />
          <text x={705} y={545} textAnchor="middle" fontSize={24} fontWeight={800} fill="#fff">32 A</text>
        </g>
        <g opacity={dcO}>
          <Charger x={1150} y={760} big label="DC" />
          <Fan x={1150} y={640} t={Math.max(0, t - tFan)} o={fadeIn(t, tFan)} />
          <Arrow x1={1230} y1={680} x2={1390} y2={680} p={prog(t, tCont)} color={C.red} w={9} />
          <Car x={1530} y={700} s={1.15} />
          <g opacity={fadeIn(t, tCont)}><Battery x={1530} y={600} level={0.75} /></g>
        </g>
      </Svg>
      <Label x={540} y={300} o={fadeIn(t, 0.2)} size={38}>Charge AC</Label>
      <Label x={540} y={350} o={fadeIn(t, 0.4)} size={26} bold={false} color={C.sub}>Le chargeur embarqué convertit et limite</Label>
      <Label x={540} y={800} o={fadeIn(t, tPoids)} size={30} color={C.red}>Plus d'ampères = chargeur plus lourd et plus gros</Label>
      <Label x={1380} y={300} o={dcO} size={38}>Charge DC</Label>
      <Label x={1380} y={350} o={dcO} size={26} bold={false} color={C.sub}>Le chargeur est dans la borne</Label>
      <Label x={1380} y={800} o={fadeIn(t, tFan)} size={30}>Ventilateur, câbles refroidis, courant continu vers la batterie</Label>
    </AbsoluteFill>
  );
};

/* ---------- 2. Bidirectional ---------- */
const V2g: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tBat = at("bâtiment"), tRes = at("réseau"), tVent = at("vent"), tRei = at("réinjecter"), tRem = at("rémunéré"), tCoup = at("coupure");
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Bidirectionnel : la voiture rend de l'énergie" t={t} />
      <Svg>
        <Car x={960} y={640} s={1.3} />
        <g opacity={fadeIn(t, 0.2)}><Battery x={960} y={520} level={0.6} w={140} /></g>
        <g opacity={fadeIn(t, tBat)}>
          <rect x={250} y={430} width={260} height={300} fill={C.grey} rx={8} />
          {[0, 1, 2].map((r) => [0, 1, 2].map((c) => <rect key={r + "-" + c} x={280 + c * 80} y={460 + r * 80} width={50} height={50} fill={t > tCoup ? "#ffd75e" : "#cfd6df"} />))}
          <Arrow x1={760} y1={600} x2={540} y2={600} p={prog(t, tBat)} color={C.green} w={9} />
        </g>
        <g opacity={fadeIn(t, tRes)}>
          <path d="M1560,730 L1610,430 L1660,730 M1575,640 L1645,640 M1590,540 L1630,540 M1540,470 L1680,470" stroke={C.ink} strokeWidth={10} fill="none" />
          <Arrow x1={1160} y1={600} x2={1500} y2={600} p={prog(t, tRes)} color={C.green} w={9} both />
        </g>
      </Svg>
      <Label x={380} y={760} o={fadeIn(t, tBat)} size={32}>Bâtiment</Label>
      <Label x={1610} y={760} o={fadeIn(t, tRes)} size={32}>Réseau</Label>
      <Label x={1330} y={300} o={fadeIn(t, tVent)} size={30} color={C.green} w={700}>Énergie bon marché (vent, soleil) : on charge</Label>
      <Label x={1330} y={350} o={fadeIn(t, tRei)} size={30} color={C.red} w={700}>Réseau en tension : on réinjecte</Label>
      <Pill x={960} y={790} o={fadeIn(t, tRem)} bg={C.green}>Client rémunéré par contrat</Pill>
      <Label x={380} y={820} o={fadeIn(t, tCoup)} size={28} color={C.amber} w={520}>Coupure : la voiture alimente la maison</Label>
    </AbsoluteFill>
  );
};

/* ---------- 3. Bathtub ---------- */
const Baignoire: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tRob = at("robinet"), tAcc = at("accumulée"), tCap = at("capacité"), tMul = at("multipliés"), tJam = at("jamais");
  const level = interpolate(t, [tRob, tCap + 1.5], [0.05, 0.85], clamp);
  const flow = t > tRob ? 1 : 0;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Kilowatt et kilowattheure : l'image de la baignoire" t={t} />
      <Svg>
        <defs><clipPath id="tub"><path d="M1000,460 L1640,460 L1600,760 Q1590,800 1550,800 L1090,800 Q1050,800 1040,760 Z" /></clipPath></defs>
        <rect x={1000} y={800 - 340 * level} width={640} height={340} fill={C.water} opacity={0.75} clipPath="url(#tub)" />
        <path d="M980,460 L1660,460 L1615,765 Q1600,815 1550,815 L1090,815 Q1040,815 1025,765 Z" fill="none" stroke={C.ink} strokeWidth={12} strokeLinejoin="round" />
        <path d="M1090,815 L1070,860 M1550,815 L1570,860" stroke={C.ink} strokeWidth={12} strokeLinecap="round" />
        <path d="M1120,300 L1120,250 L1250,250 L1250,330" fill="none" stroke={C.grey} strokeWidth={22} strokeLinecap="round" />
        <rect x={1100} y={232} width={40} height={20} fill={C.grey} />
        {flow ? <rect x={1240} y={340} width={20} height={800 - 340 * level - 340} fill={C.water} opacity={0.85} /> : null}
      </Svg>
      <div style={{ position: "absolute", left: 200, top: 300, width: 700 }}>
        <div style={{ opacity: fadeIn(t, tRob), transform: "translateX(" + (1 - fadeIn(t, tRob)) * -20 + "px)", background: "#fff", borderRadius: 22, padding: "28px 34px", marginBottom: 30, borderLeft: "10px solid " + C.water }}>
          <div style={{ fontSize: 30, color: C.sub, fontWeight: 600 }}>Le robinet, un débit</div>
          <div style={{ fontSize: 50, fontWeight: 800, color: C.ink }}>Puissance · kW</div>
          <div style={{ fontSize: 28, color: C.sub, fontWeight: 600 }}>comme des litres par heure</div>
        </div>
        <div style={{ opacity: fadeIn(t, tAcc), transform: "translateX(" + (1 - fadeIn(t, tAcc)) * -20 + "px)", background: "#fff", borderRadius: 22, padding: "28px 34px", borderLeft: "10px solid " + C.green }}>
          <div style={{ fontSize: 30, color: C.sub, fontWeight: 600 }}>L'eau dans la baignoire</div>
          <div style={{ fontSize: 50, fontWeight: 800, color: C.ink }}>Énergie · kWh</div>
          <div style={{ fontSize: 28, color: C.sub, fontWeight: 600 }}>comme des litres</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 820, display: "flex", gap: 50, alignItems: "center" }}>
        <div style={{ opacity: fadeIn(t, tMul), fontSize: 64, fontWeight: 800, color: C.ink }}>kWh = kW × h</div>
        <div style={{ opacity: fadeIn(t, tJam), fontSize: 56, fontWeight: 800, color: C.red, position: "relative" }}>
          kW/h
          <div style={{ position: "absolute", left: -8, right: -8, top: "50%", height: 8, background: C.red, transform: "rotate(-12deg) scaleX(" + prog(t, tJam + 0.2, 0.4) + ")" }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 4. Minimum rule ---------- */
const Minimum: D = ({ ctx }) => {
  const { t, at } = ctx;
  const rows = [
    { at: at("vingt"), a: "Borne 22 kW", b: "Voiture 11 kW", r: "11 kW" },
    { at: at("monophasée"), a: "Borne mono 7 kW", b: "Voiture 11 kW", r: "7 kW" },
    { at: at("continu"), a: "Borne DC 100 kW", b: "Renault 4 sans option : 80 kW", r: "80 kW" },
  ];
  const tPire = at("pire");
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="On calcule avec le minimum des deux" t={t} />
      <div style={{ position: "absolute", left: 200, top: 290, width: 1520 }}>
        {rows.map((r, i) => {
          const o = fadeIn(t, r.at, 0.5);
          const ro = fadeIn(t, r.at + 0.9, 0.4);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 34, opacity: o, transform: "translateY(" + (1 - o) * 20 + "px)" }}>
              <div style={{ flex: "0 0 460px", background: "#fff", borderRadius: 18, padding: "26px 30px", fontSize: 36, fontWeight: 700, color: C.ink }}>{r.a}</div>
              <div style={{ fontSize: 40, fontWeight: 800, color: C.sub }}>+</div>
              <div style={{ flex: "0 0 560px", background: "#fff", borderRadius: 18, padding: "26px 30px", fontSize: 36, fontWeight: 700, color: C.ink }}>{r.b}</div>
              <div style={{ fontSize: 44, fontWeight: 800, color: C.sub, opacity: ro }}>→</div>
              <div style={{ background: C.red, color: "#fff", borderRadius: 18, padding: "22px 30px", fontSize: 46, fontWeight: 800, opacity: ro, transform: "scale(" + (0.8 + 0.2 * ro) + ")" }}>{r.r}</div>
            </div>
          );
        })}
      </div>
      <Pill x={960} y={830} o={fadeIn(t, tPire)} bg={C.ink}>Option du véhicule inconnue : on prend le pire cas</Pill>
    </AbsoluteFill>
  );
};

/* ---------- 5. Boat (cos phi) ---------- */
const Bateau: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tBat = at("bateau"), tCorde = at("corde"), tAv = at("avancer"), tCote = at("côté"), tAxe = at("axe");
  const align = prog(t, tAxe, 1.2);
  const px = 560 + 560 * align, py = 820 - 170 * align; // person position moves to align with the boat axis
  const bx = 1250, by = 560;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Cos φ : tirer un bateau depuis la berge" t={t} />
      <Svg>
        <rect x={0} y={430} width={W} height={260} fill="#bfdcf5" opacity={fadeIn(t, 0.2)} />
        <rect x={0} y={690} width={W} height={390} fill="#d9cfb8" opacity={fadeIn(t, 0.2)} />
        <g opacity={fadeIn(t, tBat)}>
          <path d={"M" + (bx - 150) + "," + (by - 20) + " L" + (bx + 120) + "," + (by - 20) + " L" + (bx + 170) + "," + (by - 60) + " L" + (bx + 150) + "," + (by + 30) + " L" + (bx - 130) + "," + (by + 30) + " Z"} fill={C.grey} />
          <rect x={bx - 60} y={by - 90} width={90} height={70} fill="#9aa5b1" />
        </g>
        <g opacity={fadeIn(t, tCorde)}>
          <line x1={px} y1={py - 60} x2={bx + 160} y2={by - 40} stroke="#7a5a2f" strokeWidth={6} />
          <circle cx={px} cy={py - 110} r={26} fill={C.ink} />
          <rect x={px - 22} y={py - 84} width={44} height={84} rx={14} fill={C.ink} />
        </g>
        <Arrow x1={bx + 190} y1={by - 10} x2={bx + 430} y2={by - 10} p={prog(t, tAv)} color={C.green} w={12} />
        <g opacity={1 - align}><Arrow x1={bx + 60} y1={by + 50} x2={bx + 60} y2={by + 190} p={prog(t, tCote)} color={C.amber} w={12} /></g>
      </Svg>
      <Label x={1540} y={470} o={fadeIn(t, tAv)} size={32} color={C.green} w={520}>Puissance active : fait avancer, charge la voiture</Label>
      <Label x={1080} y={770} o={fadeIn(t, tCote) * (1 - align)} size={32} color={C.amber} w={560}>Puissance réactive : tire de côté, pas voulue</Label>
      <Pill x={960} y={900} o={fadeIn(t, tAxe + 0.6)} bg={C.ink}>Borne de recharge : on tire dans l'axe, cos φ = 1</Pill>
    </AbsoluteFill>
  );
};

/* ---------- 6. Load management ---------- */
const Pilotage: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tMul = at("multiplie"), tOrd = at("ordinateur"), t1 = at("premières"), t3 = at("nouvelle"), t4 = at("quatre"), t6 = at("six"), tRet = at("retient");
  // 66 kW available: three cars charge at 22 kW, each new arrival then slows everyone down
  const arrivals = [t1, t1 + 0.5, t1 + 1.0, t3, t3 + 1.2, t3 + 2.2];
  // continuous number of charging cars, so that shares glide instead of jumping
  const n = arrivals.reduce((acc, a) => acc + interpolate(t, [a, a + 0.8], [0, 1], { ...clamp, easing: ease }), 0);
  const total = 66;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Le pilotage partage la puissance du parc" t={t} />
      <div style={{ position: "absolute", left: 200, top: 300, display: "flex", gap: 34, alignItems: "flex-end", height: 360 }}>
        {arrivals.map((a, i) => {
          const on = t >= a;
          const share = Math.min(22, total / Math.max(1, n)) * interpolate(t, [a, a + 0.8], [0, 1], { ...clamp, easing: ease });
          const hgt = interpolate(share, [0, 22], [0, 300]);
          return (
            <div key={i} style={{ width: 120, textAlign: "center", opacity: fadeIn(t, tOrd - 0.2 + i * 0.08) }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: C.ink, marginBottom: 8, opacity: on ? 1 : 0.3 }}>{on ? Math.round(share) + " kW" : "libre"}</div>
              <div style={{ height: 300, background: "#e3e7ec", borderRadius: 14, position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: hgt, background: C.amber }} />
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: hgt, background: C.green, opacity: interpolate(share, [18, 22], [0, 1], clamp) }} />
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.sub, marginTop: 10 }}>Borne {i + 1}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 1180, top: 320, width: 560 }}>
        <div style={{ opacity: fadeIn(t, tMul), fontSize: 36, fontWeight: 700, color: C.ink, marginBottom: 26 }}>Rarement : puissance × nombre de bornes</div>
        <div style={{ opacity: fadeIn(t, tOrd), fontSize: 32, fontWeight: 600, color: C.sub, marginBottom: 26 }}>Un ordinateur de pilotage répartit la puissance disponible</div>
        <div style={{ opacity: fadeIn(t, t4), background: C.ink, color: "#fff", borderRadius: 16, padding: "18px 24px", fontSize: 34, fontWeight: 800 }}>Plus de 4 bornes : ÷ 2</div>
      </div>
      <div style={{ position: "absolute", left: 200, top: 800, fontSize: 60, fontWeight: 800, color: C.ink, display: "flex", gap: 40, alignItems: "center" }}>
        <span style={{ opacity: fadeIn(t, t6), position: "relative" }}>6 × 22 kW = 132 kW
          <span style={{ position: "absolute", left: -6, right: -6, top: "52%", height: 7, background: C.red, transform: "scaleX(" + prog(t, tRet, 0.4) + ")", transformOrigin: "left" }} />
        </span>
        <span style={{ opacity: fadeIn(t, tRet), color: C.red }}>→ 66 kW</span>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 7. Voltage drop ---------- */
const Chute: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tTgbt = at("tgbt"), tBleu = at("bleue"), tVert = at("verte"), tSom = at("somme");
  const box = (x: number, label: string, o: number) => (
    <div style={{ position: "absolute", left: x - 150, top: 420, width: 300, height: 150, background: C.ink, color: "#fff", borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36, fontWeight: 800, opacity: o, textAlign: "center" }}>{label}</div>
  );
  const pb = prog(t, tBleu), pv = prog(t, tVert), ps = prog(t, tSom, 1.2);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Chute de tension : moins de 5 % du TGBT à la borne" t={t} />
      <Svg>
        <line x1={560} y1={495} x2={560 + 300 * pb} y2={495} stroke={C.blue} strokeWidth={22} strokeLinecap="round" />
        <line x1={1160} y1={495} x2={1160 + 300 * pv} y2={495} stroke={C.green} strokeWidth={22} strokeLinecap="round" />
      </Svg>
      {box(410, "TGBT", fadeIn(t, tTgbt))}
      {box(1010, "Tableau IRVE", fadeIn(t, tBleu))}
      {box(1610, "Borne", fadeIn(t, tVert))}
      <Label x={710} y={540} o={fadeIn(t, tBleu)} size={30} color={C.blue} w={300}>Feuille bleue</Label>
      <Label x={1310} y={540} o={fadeIn(t, tVert)} size={30} color={C.green} w={300}>Feuille verte</Label>
      <div style={{ position: "absolute", left: 360, top: 700, width: 1200, opacity: fadeIn(t, tSom) }}>
        <div style={{ fontSize: 36, fontWeight: 800, color: C.ink, marginBottom: 18 }}>Chute bleue + chute verte &lt; 5 %</div>
        <div style={{ position: "relative", height: 56, background: "#e3e7ec", borderRadius: 28, overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 1200 * 0.38 * ps, background: C.blue }} />
          <div style={{ position: "absolute", left: 1200 * 0.38 * ps, top: 0, bottom: 0, width: 1200 * 0.3 * ps, background: C.green }} />
          <div style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: 6, background: C.red }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, fontWeight: 700, color: C.sub, marginTop: 10 }}><span>0 %</span><span style={{ color: C.red }}>5 %</span></div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 8. Cascading (filiation) ---------- */
const Filiation: D = ({ ctx }) => {
  const { t, at } = ctx;
  const tPhoto = at("photographie"), tRef = at("référence"), tAm = at("amont"), tPro = at("protège"), tFil = at("filiation"), tSec = at("sectionneur");
  const brk = (y: number, w: number, label: string, sub: string, o: number, color: string) => (
    <div style={{ position: "absolute", left: 760 - w / 2, top: y, width: w, background: "#fff", borderRadius: 20, borderLeft: "12px solid " + color, padding: "22px 28px", opacity: o, transform: "translateY(" + (1 - o) * 18 + "px)" }}>
      <div style={{ fontSize: 36, fontWeight: 800, color: C.ink }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 600, color: C.sub, marginTop: 6 }}>{sub}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Title text="Pourquoi photographier le disjoncteur général" t={t} />
      {brk(290, 620, "Disjoncteur général du bâtiment", "En amont · référence relevée sur la photo du TGBT", fadeIn(t, tPhoto), C.ink)}
      <Pill x={1300} y={320} o={fadeIn(t, tRef)} bg={C.ink}>Marque et référence</Pill>
      <Svg><Arrow x1={760} y1={460} x2={760} y2={600} p={prog(t, tPro)} color={C.green} w={12} /></Svg>
      {brk(620, 520, "Notre disjoncteur IRVE", "En aval, protégé par celui du dessus", fadeIn(t, tAm), C.red)}
      <div style={{ position: "absolute", left: 1120, top: 560, width: 620, opacity: fadeIn(t, tFil), background: C.green, color: "#fff", borderRadius: 20, padding: "24px 28px", fontSize: 32, fontWeight: 800, lineHeight: 1.25 }}>Filiation : même marque, coupure rapide en amont → disjoncteur aval plus petit</div>
      <div style={{ position: "absolute", left: 1120, top: 780, width: 620, opacity: fadeIn(t, tSec), fontSize: 30, fontWeight: 700, color: C.sub }}>Un sectionneur n'entre pas dans le calcul</div>
    </AbsoluteFill>
  );
};

export const DIAGRAMS: Record<string, D> = { acdc: AcDc, v2g: V2g, baignoire: Baignoire, minimum: Minimum, bateau: Bateau, pilotage: Pilotage, chute: Chute, filiation: Filiation };

