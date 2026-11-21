import React from "react";
import { Composition } from "remotion";
import { InterfaceTour, tourMetadata, type TourProps } from "./InterfaceTour";

// Les vraies données arrivent par --props=<props.json> (kit tuto-interface, README) ; ces valeurs ne servent
// qu'à ouvrir le studio Remotion sans fichier. L'habillage vient de styles/<nom>/kit.json (scripts/studio_style.py).
const defaults: TourProps = {
  video: "raw.mp4",
  timeline: { fps: 60, width: 3840, height: 2160, zoom: 2, frames: [{ cursor: { x: 960, y: 540, scale: 1 } }], events: [] },
  camera: { keyframes: [{ frame: 0, scale: 1, x: 1920, y: 1080 }] },
  look: {
    name: "charte", frame: "rounded", background: "#F0F0F2", halo: "#FFFFFF", window: "#FFFFFF", ink: "#1D1D1B", muted: "#6B6B70",
    accent: "#e3342f", onAccent: "#FFFFFF", dialog: { border: "#1D1D1B", paper: "rgba(17,17,17,.86)", ink: "#FFFFFF", radius: 18 },
    label: "TUTORIEL", closingLabel: "À RETENIR",
  },
  opening: { title: "Prendre en main l'outil" },
  closing: { lines: ["Ce qu'il faut retenir"] },
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="InterfaceTour"
    component={InterfaceTour}
    width={3840}
    height={2160}
    fps={60}
    durationInFrames={60}
    defaultProps={defaults}
    calculateMetadata={tourMetadata}
  />
);

