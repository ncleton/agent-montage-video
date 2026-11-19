import { Composition } from "remotion";
import { FormationVideo, meta, totalFrames } from "./FormationVideo";

export const RemotionRoot: React.FC = () => (
  <Composition id="Formation" component={FormationVideo} durationInFrames={totalFrames()} fps={meta.fps} width={meta.width} height={meta.height} />
);

