import { Composition } from "remotion";
import { EssentielVideo, meta, totalFrames } from "./EssentielVideo";

export const RemotionRoot: React.FC = () => (
  <Composition id="Essentiel" component={EssentielVideo} durationInFrames={totalFrames()} fps={meta.fps} width={meta.width} height={meta.height} />
);

