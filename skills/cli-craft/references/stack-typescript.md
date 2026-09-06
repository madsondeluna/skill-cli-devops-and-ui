# TypeScript (Node 20+ or Bun)

The stack of Claude Code and Gemini CLI. Choose it when the tool ships on npm, when the team knows React, or when a component model for a streaming REPL (shape 3) pays off.

| Shape | Libraries |
|---|---|
| 1, 2 | `commander` (arguments, help), `picocolors` or `chalk` (color), `ora` (spinner), `cli-progress` or `listr2` (steps and progress), `cli-table3` (tables), `@inquirer/prompts` or `@clack/prompts` (prompts), `supports-color` and `supports-hyperlinks` (detection), `string-width` and `wrap-ansi` (width math) |
| 3 | `commander` for entry, `ink` (React renderer) for the transcript and input, `ink-text-input`, `ink-select-input`, `ink-spinner`, `ink-gradient` and `ink-big-text` for the banner, `marked` + `marked-terminal` or `ink-markdown` for markdown |
| 4 | `ink` with a Yoga flexbox layout, or `@opentui/react` (OpenTUI: Zig renderer, TypeScript API, used by OpenCode) when performance or a native rendering backend matters |

## Start from the template

`assets/templates/typescript/theme.ts` holds environment detection, the tiered
theme, the OKLCH gradient sampler (`gradientColors(text, phase)` returns one
hex per character for `<Text color={c}>`), `writeFrame` with synchronized
output, `installSignalHandlers` and `emit`. Copy it to `src/ui/theme.ts`; the
Ink components in this file consume it. Run `python scripts/palette.py --ink`
to regenerate the theme object from `assets/theme.json`.

Notes on the ecosystem as of 2026:

- Ink 6.x: still the default, uses Yoga for flexbox, emits DEC 2026 synchronized output since 6.7, renders only the last frame in CI (`CI` env), has `INK_SCREEN_READER` support. Maintenance has slowed; `@claude-code-kit/ink-renderer` is a community extraction of Claude Code's renderer with a pure TypeScript Yoga port and a component library (REPL, Dialog, Tabs, FuzzyPicker, ThemeProvider) that can replace `ink` for shape 3 when a batteries included REPL is wanted.
- OpenTUI: newer, faster, still moving. Prefer for shape 4 when a full screen app with many widgets is the product.
- Validation of inputs with `zod` (Claude Code's choice); config with `cosmiconfig` or a hand rolled XDG loader.
- Runtime: Bun starts faster and bundles to a single file (`bun build --compile`); Node needs `esbuild` or `tsup` and a shebang. Either way, ship one bundled file so `npx tool` starts in under 200 ms.

## Output module (`ui.ts`)

```ts
// Single place that knows about terminals. Decoration to stderr, results to stdout.
import { createSupportsColor } from "supports-color";
import { Writable } from "node:stream";

export type ColorLevel = 0 | 1 | 2 | 3;

function level(stream: NodeJS.WriteStream, when: string): ColorLevel {
  if (when === "never" || "NO_COLOR" in process.env) return 0;
  if (when === "always" || process.env.FORCE_COLOR) {
    const f = process.env.FORCE_COLOR;
    return f === "3" ? 3 : f === "2" ? 2 : 1;
  }
  const s = createSupportsColor(stream); // handles isTTY, TERM, COLORTERM, CI
  return (s ? s.level : 0) as ColorLevel;
}

export const errLevel = level(process.stderr, process.env.TOOL_COLOR ?? "auto");
export const outLevel = level(process.stdout, process.env.TOOL_COLOR ?? "auto");
export const utf8 = !process.env.TOOL_ASCII && /utf-?8/i.test(process.env.LC_ALL ?? process.env.LC_CTYPE ?? process.env.LANG ?? "");
export const animate = process.stderr.isTTY && !process.env.CI && !process.env.TOOL_NO_ANIMATION && process.env.TERM !== "dumb";
export const interactive = process.stdin.isTTY && process.stderr.isTTY && !process.env.CI;
export const width = () => process.stderr.columns ?? Number(process.env.COLUMNS) || 80;

// Semantic roles as SGR builders. Truecolor when available, 16 color fallback otherwise.
const sgr = (tc: string, basic: number) => (s: string, lv: ColorLevel = errLevel) =>
  lv === 0 ? s : lv >= 3 ? `\x1b[38;2;${tc}m${s}\x1b[39m` : `\x1b[${basic}m${s}\x1b[39m`;

export const c = {
  muted: sgr("138;143;152", 90),
  accent: sgr("122;162;247", 34),
  accent2: sgr("187;154;247", 35),
  ok: sgr("158;206;106", 32),
  warn: sgr("224;175;104", 33),
  err: sgr("247;118;142", 31),
  info: sgr("125;207;255", 36),
  bold: (s: string, lv: ColorLevel = errLevel) => (lv ? `\x1b[1m${s}\x1b[22m` : s),
  dim: (s: string, lv: ColorLevel = errLevel) => (lv ? `\x1b[2m${s}\x1b[22m` : s),
};

export const g = {
  ok: utf8 ? "\u2713" : "ok",
  err: utf8 ? "\u2717" : "x",
  warn: utf8 ? "\u25b2" : "!",
  info: utf8 ? "\u25cf" : "*",
  ptr: utf8 ? "\u276f" : ">",
};

const e = (s: string) => process.stderr.write(s + "\n");
export const ok = (m: string) => e(`${c.ok(g.ok)} ${m}`);
export const info = (m: string) => e(`${c.info(g.info)} ${m}`);
export const warn = (m: string) => e(`${c.warn("warning:")} ${m}`);
export const error = (m: string, hint?: string) => {
  e(`${c.err("error:")} ${m}`);
  if (hint) e(`  ${c.muted("hint:")} ${hint}`);
};

// Always restore the cursor and SGR on any exit path
const restore = () => { if (process.stderr.isTTY) process.stderr.write("\x1b[?25h\x1b[0m"); };
process.on("exit", restore);
process.on("SIGINT", () => { restore(); process.exit(130); });
process.on("uncaughtException", (err) => { restore(); error(err.message); process.exit(1); });
```

## Commands with Commander

```ts
import { Command, InvalidArgumentError } from "commander";
import * as ui from "./ui.js";

const program = new Command("tool")
  .description("Run and inspect AMP pipelines")
  .version("1.4.0", "-V, --version")
  .option("--color <when>", "auto, always, never", "auto")
  .option("-q, --quiet", "errors only")
  .option("-v, --verbose", "more output", (_, prev: number) => prev + 1, 0)
  .showHelpAfterError("(run --help for usage)")
  .configureOutput({ writeErr: (s) => process.stderr.write(s) })
  .addHelpText("after", `
Examples:
  tool run samples.tsv --profile docker
  tool status --json | jq .state`);

program.command("run")
  .argument("<samples>", "TSV of samples, or - for stdin")
  .option("-p, --profile <name>", "execution profile", process.env.TOOL_PROFILE ?? "docker")
  .option("--dry-run", "print the plan only")
  .option("-y, --yes", "skip confirmations")
  .action(async (samples, opts) => {
    const rows = await readSamples(samples);
    if (!opts.yes && !opts.dryRun) {
      if (!ui.interactive) { ui.error("cannot prompt: stdin is not a terminal", "pass --yes"); process.exit(2); }
      const { confirm } = await import("@inquirer/prompts");
      if (!(await confirm({ message: `Run ${rows.length} samples with ${opts.profile}?`, default: false }))) process.exit(130);
    }
    const { default: ora } = await import("ora");
    const sp = ora({ text: `aligning ${rows.length} samples`, stream: process.stderr, isEnabled: ui.animate }).start();
    try { await alignAll(rows, opts.profile); sp.succeed(); }
    catch (err) { sp.fail(); ui.error((err as Error).message); process.exit(1); }
    ui.ok(`${rows.length} samples done, report at results/report.html`);
  });

program.command("status")
  .option("--json", "machine readable output")
  .action(async (opts) => {
    const state = await loadState();
    if (opts.json) { process.stdout.write(JSON.stringify(state, null, 2) + "\n"); return; }
    printTable(state.runs); // stdout, tab separated when !process.stdout.isTTY
  });

program.parseAsync().catch((err) => { ui.error(err.message); process.exit(1); });
```

Commander details: `exitOverride()` when embedding; `InvalidArgumentError` yields exit 2 automatically with the error on stderr; dynamic `import()` for heavy dependencies keeps startup fast; `--no-` negation is built in for boolean options declared as `--no-input`.

## Ink for shape 3

Core pattern, matching Gemini CLI's layout: `<Static>` for the frozen transcript (rendered once, never re rendered), a live area for the current message and tool activity, an input at the bottom.

```tsx
import React, { useState } from "react";
import { render, Box, Text, Static, useInput, useApp, useStdout } from "ink";
import TextInput from "ink-text-input";
import Spinner from "ink-spinner";

type Item = { id: string; role: "user" | "assistant" | "tool"; text: string; status?: "ok" | "err" | "run" };

function App({ engine }: { engine: Engine }) {
  const [history, setHistory] = useState<Item[]>([]);   // frozen, goes to Static
  const [live, setLive] = useState<Item | null>(null);   // current streaming message
  const [input, setInput] = useState("");
  const { exit } = useApp();
  const { stdout } = useStdout();

  useInput((ch, key) => { if (key.ctrl && ch === "c") exit(); });

  async function submit(text: string) {
    setHistory((h) => [...h, { id: crypto.randomUUID(), role: "user", text }]);
    setInput("");
    let acc = "";
    for await (const ev of engine.run(text)) {
      if (ev.type === "delta") { acc += ev.text; setLive({ id: "live", role: "assistant", text: acc }); }
      if (ev.type === "tool") setHistory((h) => [...h, { id: ev.id, role: "tool", text: ev.summary, status: ev.status }]);
    }
    setHistory((h) => [...h, { id: crypto.randomUUID(), role: "assistant", text: acc }]);
    setLive(null);
  }

  return (
    <Box flexDirection="column" width={stdout.columns}>
      <Static items={history}>
        {(m) => (
          <Box key={m.id} paddingLeft={m.role === "user" ? 0 : 2} marginBottom={1}>
            {m.role === "user" && <Text color="#6FA3FF">{"> "}</Text>}
            {m.role === "tool" && <Text color={m.status === "err" ? "#FF7B8E" : "#6EE39C"}>{m.status === "err" ? "x " : "ok "}</Text>}
            <Text wrap="wrap">{m.text}</Text>
          </Box>
        )}
      </Static>
      {live && (
        <Box paddingLeft={2}><Text wrap="wrap">{live.text}</Text><Text color="#7CD5FF"> <Spinner type="dots" /></Text></Box>
      )}
      <Box borderStyle="round" borderColor={live ? "#3A4258" : "#6FA3FF"} paddingX={1}>
        <Text color="#6FA3FF">{"> "}</Text>
        <TextInput value={input} onChange={setInput} onSubmit={submit} placeholder="ask anything, / for commands" />
      </Box>
      <Box justifyContent="space-between" paddingX={1}>
        <Text dimColor>ctrl+c quit  / commands  ? help</Text>
        <Text dimColor>{engine.model}  ctx {engine.ctxPct}%</Text>
      </Box>
    </Box>
  );
}

const { waitUntilExit } = render(<App engine={engine} />, { patchConsole: true, exitOnCtrlC: false });
await waitUntilExit();
```

Ink rules that prevent the classic bugs:

- Everything in `<Static>` must have a stable `key`; items are rendered once and appended above the live output. Never mutate an item after it entered `Static`.
- Keep the live area under about 10 lines; Ink rewrites the whole non static area on each render, so a large live area is where flicker and CPU come from.
- `patchConsole: true` routes stray `console.log` above the UI instead of corrupting it.
- Handle `exitOnCtrlC: false` and exit yourself so the cursor and terminal modes are restored through `useApp().exit()`.
- Colors: Ink accepts hex and maps to the terminal level; check `chalk.level` (Ink uses chalk) to decide whether a gradient is worth rendering.
- Width: read `useStdout().stdout.columns` and re render on `resize` (Ink subscribes for you); pass `width` to the root `Box`.
- Test with `ink-testing-library`: `const { lastFrame, stdin } = render(<App/>); stdin.write("hello\r")`.

Slash commands and file pickers: a `useState` for the palette mode, a fuzzy filter (`fuzzysort`), `ink-select-input` or a custom list capped at 8 visible rows.

Permission prompt: a `Box` with `borderStyle="round"` and `borderColor` warn, the verbatim command in a nested `Box` with `borderStyle="single"`, an `ink-select-input` with the safe option first, `useInput` mapping Esc to deny. Render it in place of the input box, not in the live area.

## OpenTUI for shape 4

`@opentui/react` exposes `<box>`, `<text>`, `<input>`, `<select>`, `<scrollbox>` with flexbox props and a native renderer. Same architecture as Ink (state in React, effects for I/O) with better frame times for large screens. The API is still changing; pin the version and read the repository examples for the current component set before writing code.

## Testing and packaging

- Unit: `vitest`; CLI: spawn the built binary with `execa` and assert on stdout and stderr separately, with `env: { NO_COLOR: "1", COLUMNS: "80" }`, plus one truecolor case.
- Bundle: `bun build src/main.ts --compile --outfile tool` or `tsup src/main.ts --format esm --banner '#!/usr/bin/env node'`.
- `package.json`: `"bin": { "tool": "./dist/main.js" }`, `"engines": { "node": ">=20" }`, `"type": "module"`.
