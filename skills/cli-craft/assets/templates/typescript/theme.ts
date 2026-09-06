/**
 * Terminal environment, theme and gradient helpers for Ink based CLIs.
 *
 * Copy into `src/ui/theme.ts`. This is the only module that knows about TTYs,
 * color depth and animation. Components receive plain data and read `env`.
 * Dependencies: none at runtime beyond Node. Ink and React are used by the
 * components that import this file, not by this file.
 *
 * Pair with references/typescript-stack.md for the component patterns
 * (Static for finished output, one live region, useInput for keys).
 */

// ---------------------------------------------------------------------------
// Environment: detected once at import
// ---------------------------------------------------------------------------

export type Depth = 0 | 16 | 256 | 16777216;

export interface Env {
  stdoutTty: boolean;
  stderrTty: boolean;
  color: boolean;
  depth: Depth;
  animate: boolean;      // live redraws allowed
  interactive: boolean;  // prompts allowed
  unicode: boolean;
  width: number;
  lightBg: boolean;
}

const TOOL = (process.env.CLI_CRAFT_TOOL_NAME ?? "tool").toUpperCase();

function detectDepth(): Depth {
  const force = process.env.FORCE_COLOR;
  if (force !== undefined && force !== "" && force !== "0") {
    return force === "1" ? 16 : force === "2" ? 256 : 16777216;
  }
  if ("NO_COLOR" in process.env || process.env.TERM === "dumb") return 0;
  const ct = process.env.COLORTERM;
  if (ct === "truecolor" || ct === "24bit") return 16777216;
  const term = process.env.TERM ?? "";
  if (term.includes("256")) return 256;
  return term ? 16 : 0;
}

export function detect(): Env {
  const stdoutTty = Boolean(process.stdout.isTTY);
  const stderrTty = Boolean(process.stderr.isTTY);
  const ci = Boolean(process.env.CI);
  const dumb = process.env.TERM === "dumb";
  const depth = detectDepth();
  const lang = `${process.env.LC_ALL ?? ""}${process.env.LC_CTYPE ?? ""}${process.env.LANG ?? ""}`.toLowerCase();
  const columns = process.stderr.columns ?? Number(process.env.COLUMNS ?? 80) ?? 80;
  return {
    stdoutTty,
    stderrTty,
    color: depth > 0 && (stdoutTty || stderrTty),
    depth,
    animate: stderrTty && !ci && !dumb && !process.env[`${TOOL}_NO_ANIMATION`],
    interactive: Boolean(process.stdin.isTTY) && stderrTty && !ci,
    unicode: lang.includes("utf") && !dumb && !process.env[`${TOOL}_ASCII`],
    width: Math.min(columns > 0 ? columns : 80, 100),
    lightBg: process.env[`${TOOL}_THEME`] === "light",
  };
}

export let env: Env = detect();

/** Honor --color=auto|always|never after argument parsing. */
export function applyColorFlag(value: "auto" | "always" | "never"): void {
  if (value === "auto") return;
  const depth: Depth = value === "never" ? 0 : (env.depth || 16777216);
  env = { ...env, depth, color: depth > 0, animate: env.animate && depth > 0 };
}

// ---------------------------------------------------------------------------
// Theme roles (see references/palette.md). Ink <Text color="#hex"> accepts hex;
// on 256 and 16 color terminals use the named fallbacks.
// ---------------------------------------------------------------------------

export const roles = {
  dark: {
    fg: "#E6E9F0", muted: "#8B95A9", dim: "#5C6577", accent: "#6FA3FF", accent2: "#B49CFF",
    teal: "#3DDBC7", ok: "#6EE39C", warn: "#F2C56B", err: "#FF7B8E", info: "#7CD5FF",
    border: "#3A4258", bgPanel: "#161A26", bgSelect: "#243052",
  },
  light: {
    fg: "#1B2030", muted: "#5B6472", dim: "#8A93A3", accent: "#2358D6", accent2: "#6B33D6",
    teal: "#0F7A6E", ok: "#1B7A3E", warn: "#8A5A00", err: "#C4283A", info: "#0B6FA8",
    border: "#CDD3DE", bgPanel: "#F4F6FA", bgSelect: "#DDE6FF",
  },
  c256: {
    fg: "white", muted: "ansi256(245)", dim: "ansi256(240)", accent: "ansi256(75)", accent2: "ansi256(141)",
    teal: "ansi256(80)", ok: "ansi256(114)", warn: "ansi256(221)", err: "ansi256(210)", info: "ansi256(117)",
    border: "ansi256(238)", bgPanel: "ansi256(234)", bgSelect: "ansi256(237)",
  },
  c16: {
    fg: "white", muted: "gray", dim: "gray", accent: "blue", accent2: "magenta", teal: "cyan",
    ok: "green", warn: "yellow", err: "red", info: "cyan", border: "gray", bgPanel: "", bgSelect: "blue",
  },
} as const;

export type Role = keyof typeof roles.dark;

export function theme(): Record<Role, string> {
  if (env.depth >= 16777216) return env.lightBg ? roles.light : roles.dark;
  if (env.depth >= 256) return roles.c256 as Record<Role, string>;
  return roles.c16 as Record<Role, string>;
}

export const GRADIENT_DARK = ["#3DDBC7", "#38BDF8", "#5B9CFF", "#8B7BFF", "#C084FC"];
export const GRADIENT_LIGHT = ["#0F766E", "#0284C7", "#2358D6", "#5B3FD1", "#8A3FC4"];
export const GRADIENT_256 = ["ansi256(80)", "ansi256(75)", "ansi256(111)", "ansi256(141)"];

// ---------------------------------------------------------------------------
// Glyphs with ASCII fallback
// ---------------------------------------------------------------------------

export const glyph = () => ({
  ok: env.unicode ? "\u2713" : "ok",
  err: env.unicode ? "\u2717" : "x",
  warn: env.unicode ? "\u25B2" : "!",
  info: env.unicode ? "\u25CF" : "*",
  pointer: env.unicode ? "\u276F" : ">",
  rule: env.unicode ? "\u2500" : "-",
  barFill: env.unicode ? "\u2588" : "#",
  barEmpty: env.unicode ? "\u2591" : "-",
});

// ---------------------------------------------------------------------------
// Gradient: OKLCH interpolation, seamless phase wrap for animation
// ---------------------------------------------------------------------------

type Lab = [number, number, number];

function hexToOklab(h: string): Lab {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
  const lin = c.map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  const l = Math.cbrt(0.4122214708 * lin[0] + 0.5363325363 * lin[1] + 0.0514459929 * lin[2]);
  const m = Math.cbrt(0.2119034982 * lin[0] + 0.6806995451 * lin[1] + 0.1073969566 * lin[2]);
  const s = Math.cbrt(0.0883024619 * lin[0] + 0.2817188376 * lin[1] + 0.6299787005 * lin[2]);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function oklabToHex([L, a, b]: Lab): string {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  return "#" + lin.map((v) => {
    const c = Math.min(1, Math.max(0, v));
    const g = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
    return Math.round(g * 255).toString(16).padStart(2, "0").toUpperCase();
  }).join("");
}

/** Sample the gradient at t in [0, 1); wraps so phase shifting loops. */
export function sampleGradient(t: number, stops = env.lightBg ? GRADIENT_LIGHT : GRADIENT_DARK): string {
  const u = ((t % 1) + 1) % 1;
  const pos = u * stops.length;
  const i = Math.floor(pos) % stops.length;
  const f = pos - Math.floor(pos);
  const a = hexToOklab(stops[i]);
  const b = hexToOklab(stops[(i + 1) % stops.length]);
  return oklabToHex(a.map((x, k) => x + (b[k] - x) * f) as Lab);
}

/**
 * Per character colors for a string, for `<Text color={c}>{ch}</Text>` in Ink
 * or `chalk.hex(c)(ch)` without Ink. Falls back per color depth so callers do
 * not branch. Phase in [0, 1) drives the animation.
 */
export function gradientColors(text: string, phase = 0): string[] {
  const t = theme();
  if (env.depth < 256) return Array.from(text, () => t.accent);
  if (env.depth < 16777216) {
    return Array.from(text, (_, i) => GRADIENT_256[Math.floor((i * GRADIENT_256.length) / Math.max(1, text.length)) % GRADIENT_256.length]);
  }
  return Array.from(text, (_, i) => sampleGradient((i / Math.max(1, text.length)) * 0.6 + phase));
}

/** Animation constants from assets/theme.json. */
export const motion = { fps: 15, phaseStepDeg: 6, revealMs: 1200, spinnerHueTurnsPerSec: 0.35 } as const;

// ---------------------------------------------------------------------------
// Banner: 5x5 block font (same glyphs as the Python template)
// ---------------------------------------------------------------------------

const FONT: Record<string, string[]> = {
  A: ["01110", "10001", "11111", "10001", "10001"], B: ["11110", "10001", "11110", "10001", "11110"],
  C: ["01111", "10000", "10000", "10000", "01111"], D: ["11110", "10001", "10001", "10001", "11110"],
  E: ["11111", "10000", "11110", "10000", "11111"], F: ["11111", "10000", "11110", "10000", "10000"],
  G: ["01111", "10000", "10011", "10001", "01111"], H: ["10001", "10001", "11111", "10001", "10001"],
  I: ["11111", "00100", "00100", "00100", "11111"], J: ["00111", "00010", "00010", "10010", "01100"],
  K: ["10001", "10010", "11100", "10010", "10001"], L: ["10000", "10000", "10000", "10000", "11111"],
  M: ["10001", "11011", "10101", "10001", "10001"], N: ["10001", "11001", "10101", "10011", "10001"],
  O: ["01110", "10001", "10001", "10001", "01110"], P: ["11110", "10001", "11110", "10000", "10000"],
  Q: ["01110", "10001", "10101", "10010", "01101"], R: ["11110", "10001", "11110", "10010", "10001"],
  S: ["01111", "10000", "01110", "00001", "11110"], T: ["11111", "00100", "00100", "00100", "00100"],
  U: ["10001", "10001", "10001", "10001", "01110"], V: ["10001", "10001", "10001", "01010", "00100"],
  W: ["10001", "10001", "10101", "11011", "10001"], X: ["10001", "01010", "00100", "01010", "10001"],
  Y: ["10001", "01010", "00100", "00100", "00100"], Z: ["11111", "00010", "00100", "01000", "11111"],
  "0": ["01110", "10011", "10101", "11001", "01110"], "1": ["00100", "01100", "00100", "00100", "01110"],
  "2": ["01110", "10001", "00110", "01000", "11111"], "3": ["11110", "00001", "01110", "00001", "11110"],
  "4": ["00010", "00110", "01010", "11111", "00010"], "5": ["11111", "10000", "11110", "00001", "11110"],
  "6": ["01110", "10000", "11110", "10001", "01110"], "7": ["11111", "00010", "00100", "01000", "01000"],
  "8": ["01110", "10001", "01110", "10001", "01110"], "9": ["01110", "10001", "01111", "00001", "01110"],
  "-": ["00000", "00000", "01110", "00000", "00000"], ".": ["00000", "00000", "00000", "00000", "00100"],
  "_": ["00000", "00000", "00000", "00000", "11111"], " ": ["00000", "00000", "00000", "00000", "00000"],
};

/**
 * Render `word` in the 5x5 block font, one string per row. Degrades to a
 * single upper case line when the art would overflow or the locale is not
 * UTF-8, so callers never branch.
 */
export function asciiArt(word: string): string[] {
  const w = word.toUpperCase();
  if (!env.unicode || w.length * 6 > env.width) return [w];
  const cell = "\u2588";
  const rows = Array.from({ length: 5 }, () => "");
  for (const ch of w) {
    const g = FONT[ch] ?? FONT[" "];
    for (let r = 0; r < 5; r++) {
      rows[r] += Array.from(g[r], (b) => (b === "1" ? cell : " ")).join("") + " ";
    }
  }
  return rows.map((r) => r.replace(/\s+$/, ""));
}

/**
 * Per character colors for a block of art, one continuous gradient across the
 * full width. Feed row by row into Ink <Text> spans, or into chalk.hex.
 */
export function gradientBlock(lines: string[], phase = 0): string[][] {
  const width = Math.max(...lines.map((l) => l.length), 1);
  const t = theme();
  return lines.map((line) =>
    Array.from(line, (_, x) =>
      env.depth >= 16777216 ? sampleGradient((x / width) * 0.6 + phase) : t.accent));
}

/**
 * Gradient color for a live region at the current time. Call it on every
 * redraw of a spinner or progress bar so the hue cycles while the region is
 * visible; stop calling it once the region freezes.
 */
export function cyclingColor(offset = 0): string {
  if (env.depth < 16777216) return theme().accent;
  return sampleGradient(Date.now() / 1000 * motion.spinnerHueTurnsPerSec + offset);
}

// ---------------------------------------------------------------------------
// Terminal hygiene
// ---------------------------------------------------------------------------

/** Wrap a raw frame write in DEC synchronized output so terminals paint once. */
export function writeFrame(stream: NodeJS.WriteStream, frame: string): void {
  stream.write(`\x1b[?2026h${frame}\x1b[?2026l`);
}

/** Restore the cursor and exit 130 on Ctrl-C, even mid animation. */
export function installSignalHandlers(): void {
  process.on("SIGINT", () => {
    process.stderr.write("\x1b[?25h\x1b[?2026l\r\x1b[K");
    process.stderr.write(env.color ? `\x1b[90minterrupted\x1b[0m\n` : "interrupted\n");
    process.exit(130);
  });
}

/** Primary result to stdout: JSON when asked or piped, otherwise the human form. */
export function emit(data: unknown, asJson: boolean, human: () => string): void {
  if (asJson || !env.stdoutTty) {
    process.stdout.write(JSON.stringify(data) + "\n");
    return;
  }
  process.stdout.write(human() + "\n");
}
