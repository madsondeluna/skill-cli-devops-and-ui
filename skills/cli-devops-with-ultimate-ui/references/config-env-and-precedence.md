# Configuration, Environment, and Precedence

Where settings come from (flags, environment variables, and config files) and the order in which
they win. Match the configuration mechanism to how often a value changes, follow a clear precedence
chain, use standard locations (XDG), and never put secrets in env vars.

**When this applies:** designing config sources, env-var conventions, config file format/location, or
resolving conflicts between settings.

## Principles

- **Match mechanism to volatility**:
 - changes per run (debug, dry-run) → **flags** (maybe env vars too);
 - stable per user/project (paths, proxy, color) → **flags + env vars**;
 - stable for all users of a project (build config) → **version-controlled file**.
- **Treat config as untrusted input:** validate paths/URLs, don't assume numeric formats
 (`1_000`, `1e3`), fail safely.

## Precedence (highest wins): recommended order

Recommended chain:

1. Command-line flags
2. Shell environment variables
3. Project-level config (e.g., `.env` or a project config file)
4. User-level config (e.g., `~/.config/tool/config.toml`)
5. System-wide config (e.g., `/etc/tool/config`)

```
# flag beats env beats file
$ TOOL_REGION=us tool deploy --region eu     # uses eu (flag wins)
```
Document the resolved order so users can predict behavior.

## Environment variables

- Names: UPPERCASE letters, digits, underscores, not starting with a digit; keep
 values single-line. Booleans: accept presence-as-true or
 `1/true/enabled` vs `0/false/disabled`.
- Honor standard general-purpose vars where relevant: `NO_COLOR`/`FORCE_COLOR`, `DEBUG`, `EDITOR`,
 `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`, `PAGER`, `TERM`, `TMPDIR`, `HOME`, `LINES`/`COLUMNS`. Don't commandeer widely-used names.
- Support reading a project `.env` for values that don't change within a directory, but **don't treat
 `.env` as your real config format** (no history, string-only, easy to leak).

## Config files

- **Use standard locations**: follow the XDG Base Directory spec (`~/.config/tool/`) to
 avoid dotfile sprawl.
- Formats: TOML/JSON/YAML or simple line-based; pick human-readable and diffable. Code-as-config
 (JS/Lua/HCL/Jsonnet) is powerful but needs heavy docs, error handling, and versioning, only for
 very stable APIs.
- **Ask consent before modifying files you don't own:** prefer writing a new file (e.g.
 `/etc/cron.d/tool`) over appending to a shared one; if you must append, mark it with a dated comment.

## Secrets

- **Never read secrets from environment variables or flags**: they leak via exported
 vars, `ps`, shell history, `docker inspect`, `systemctl show`. Use credential files,
 pipes, sockets, or a secret manager. See `arguments-and-flags.md`, `prompts-and-confirmation.md`.

## Windows / PowerShell callouts

- XDG is a freedesktop (Linux) spec; on Windows use `%APPDATA%`/`%LOCALAPPDATA%`
 (and consider `%XDG_CONFIG_HOME%` if set). Env vars are case-insensitive on Windows but treat them
 as UPPERCASE for portability. In PowerShell, env vars are `$env:NAME`, set per-process; persisting
 to User/Machine scope uses `[Environment]::SetEnvironmentVariable`: document this if your tool
 tells users to set variables.
- `.env` loading and proxy variables behave the same cross-platform; keep one precedence chain on all
 OSes.

## Edge cases / anti-patterns

- **Don't** invent a precedence that contradicts the documented order, or leave it undocumented.
- **Don't** silently overwrite a user's existing config; back up or append-with-marker.
- Optional-value flags interacting with env defaults: define what an explicit `--flag` with no value
 means vs the env default (see `arguments-and-flags.md`).

## Do / Don't

- **Do** layer flags > env > project > user > system, and document it.
- **Do** use XDG/`%APPDATA%` locations and validate all config input.
- **Don't** keep secrets in env vars or `.env` you might commit.
- **Don't** append to files you don't own without consent and a marker.

## Related

`arguments-and-flags.md` · `prompts-and-confirmation.md` · `color-and-styling.md` ·
`interactivity-tty-and-ci.md`
