import React from "react";
import { Composition } from "remotion";
import { InterfaceTour, tourMetadata, type TourProps } from "./InterfaceTour";

// Les vraies données arrivent par --props=<props.json> (kit tuto-interface, README) ; ces valeurs ne servent
// qu'à ouvrir le studio Remotion sans fichier.
const defaults: TourProps = {
  video: "raw.mp4",
  timeline: { fps: 60, width: 3840, height: 2160, zoom: 2, frames: [{ cursor: { x: 960, y: 540, scale: 1 } }], events: [] },
  camera: { keyframes: [{ frame: 0, scale: 1, x: 1920, y: 1080 }] },
  theme: "light",
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
