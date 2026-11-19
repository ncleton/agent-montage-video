// Renders review stills at half resolution: node stills.mjs <frames file "id frame" per line> <out dir>
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const [framesFile, outDir] = process.argv.slice(2);
const items = fs.readFileSync(framesFile, "utf8").trim().split("\n").map((l) => l.trim().split(/\s+/));
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
const composition = await selectComposition({ serveUrl, id: "Formation" });
for (const [id, frame] of items) {
  const output = path.join(outDir, String(frame).padStart(6, "0") + "-" + id + ".png");
  await renderStill({ serveUrl, composition, frame: Number(frame), output, scale: 0.5 });
  console.log("still", id, frame);
}

