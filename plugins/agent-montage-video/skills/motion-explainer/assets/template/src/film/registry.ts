/**
 * Chapter id -> component for the full film. A missing chapter stops rendering
 * with the exact component to implement and register.
 *
 * To register chapter C03 (component in src/film/chapters/C03/index.tsx, `export const C03`):
 *   1. add   import { C03 } from "./chapters/C03";
 *   2. add   C03,   inside CHAPTER_COMPONENTS
 * One line each, keep them sorted. Only the orchestrator edits this file. Chapter previews do
 * NOT read it, so a broken chapter can only break the full film render, never another preview.
 */
import type React from "react";
import type { ChapterId } from "./chapters";

// --- chapter imports (one per line, sorted) ---
import { C01 } from "./chapters/C01";
import { C02 } from "./chapters/C02";

export const CHAPTER_COMPONENTS: Partial<Record<ChapterId, React.FC>> = {
  // --- registered chapters (one per line, sorted) ---
  C01,
  C02,
};

export const chapterComponent = (id: ChapterId): React.FC => {
  const Chapter = CHAPTER_COMPONENTS[id];
  if (!Chapter) {
    throw new Error(`Missing chapter ${id}: implement src/film/chapters/${id}/index.tsx and register it in src/film/registry.ts before rendering.`);
  }
  return Chapter;
};
