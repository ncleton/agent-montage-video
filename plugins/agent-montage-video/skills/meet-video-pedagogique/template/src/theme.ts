import { Easing, interpolate } from "remotion";

export const C = { bg: "#f4f5f7", ink: "#1d232c", sub: "#5b6573", red: "#e30613", grey: "#444444", line: "#d9dde3", blue: "#1f6feb", green: "#14a05a", amber: "#f59e0b", card: "#ffffff", water: "#3b9be8" };
export const ease = Easing.bezier(0.45, 0, 0.2, 1);
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const fadeIn = (t: number, t0: number, d = 0.4) => interpolate(t, [t0, t0 + d], [0, 1], { ...clamp, easing: ease });
export type Ctx = { t: number; at: (k: string | null | undefined) => number; dur: number; scene: { id: string } };
export type Visual = { type: string; [k: string]: unknown };

