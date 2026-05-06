# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

GitHub Spec Kit — the `specify` Python CLI that bootstraps repositories for Spec-Driven Development by installing slash-command templates, scripts, and context files into one of ~30 supported AI coding agents. It is **not** an application; it is tooling that emits assets into other people's projects.

Read these first for deeper context:
- `README.md` — user-facing overview and `/speckit.*` workflow.
- `DEVELOPMENT.md` — orientation for modifying Spec Kit itself.
- `AGENTS.md` — authoritative guide for adding/modifying integrations (base classes, required fields, common pitfalls). **Read this before touching anything under `src/specify_cli/integrations/`.**
- `CONTRIBUTING.md` — manual-test reporting template + which tests map to which slash commands.

## Common commands

All Python work goes through `uv` (do not invoke `pip`/`python` directly — the venv is managed by uv).

```bash
# One-time setup
uv sync --extra test                    # installs runtime + test deps into .venv
uv pip install -e .                     # makes the local working tree's `specify` binary active

# Run the CLI from the working tree
uv run specify --help
uv run specify init /tmp/sk-test --integration claude    # smoke-test scaffolding
uv run specify init /tmp/sk-test --integration codex --integration-options="--skills"

# Tests
uv run pytest                                            # full suite
uv run pytest tests/test_extensions.py -v                # single file
uv run pytest tests/test_extensions.py::TestName::test_x # single test
uv run pytest tests/integrations/test_integration_<key_with_underscores>.py -v
uv run pytest tests/test_agent_config_consistency.py -q  # run after changing agent metadata or wiring

# Lint
uvx ruff check src/                     # Python lint (CI gate)
markdownlint-cli2 '**/*.md' '!extensions/**/*.md'   # markdown lint (CI gate; config in .markdownlint-cli2.jsonc)
```

CI runs `ruff check src/` + `pytest` on Python 3.11/3.12/3.13 (Linux + Windows) and markdownlint. Bash-based tests auto-skip on Windows unless Git-for-Windows bash is on PATH (see `tests/conftest.py::_has_working_bash`).

## Architecture — the parts that aren't obvious from `ls`

### 1. Integration registry is the single source of truth

`src/specify_cli/integrations/` holds one subpackage per AI agent. Each agent is a class that inherits from one of the base classes in `base.py`:

| Base class | When to use |
|---|---|
| `MarkdownIntegration` | Standard `.md` slash commands (most agents) |
| `TomlIntegration` | TOML command files (Gemini, Tabnine) |
| `YamlIntegration` | YAML recipes (Goose) |
| `SkillsIntegration` | `speckit-<name>/SKILL.md` skill directories (Codex) |
| `IntegrationBase` (direct) | Custom output (Copilot's `.agent.md` + `.prompt.md` + VS Code settings) |

`integrations/__init__.py::_register_builtins()` imports + registers every integration into `INTEGRATION_REGISTRY`. **`src/specify_cli/__init__.py::_build_agent_config()` derives the entire `AGENT_CONFIG` dict from this registry** — there is no parallel list of agents to keep in sync. Adding an agent = new subpackage + one import + one `_register()` line.

Two non-obvious rules from `AGENTS.md` that will bite you:
- For `requires_cli: True`, `key` must equal the actual CLI executable name (`shutil.which(key)` is called). Use `"cursor-agent"`, not `"cursor"`.
- Hyphenated keys map to underscore-named package dirs and test files (`key="kiro-cli"` → `integrations/kiro_cli/` → `tests/integrations/test_integration_kiro_cli.py`).

### 2. Templates: install-time vs runtime resolution

Two distinct flows, easy to confuse:

- **Command files** (`templates/commands/*.md`) are processed at **install time** by `specify init` / `specify extension add` / `specify preset add` and written into the agent's directory (e.g. `.claude/commands/`, `.gemini/commands/`). The integration's `registrar_config` controls output dir, file extension, and the `args` placeholder (`$ARGUMENTS` for markdown, `{{args}}` for TOML/YAML, `{{parameters}}` for Forge).
- **Page templates** (`templates/{spec,plan,tasks,checklist,constitution}-template.md`) and helper scripts (`scripts/bash/*.sh`, `scripts/powershell/*.ps1`) are consumed at **runtime** by the agent when the user invokes a slash command. The `{SCRIPT}` placeholder gets substituted to the actual script path.

### 3. Layered template resolution (highest priority wins)

When the agent expands a template at runtime, the lookup order is:

1. `.specify/templates/overrides/` — project-local one-off overrides
2. Installed presets (`.specify/presets/templates/`)
3. Installed extensions (`.specify/extensions/templates/`)
4. Core defaults (`.specify/templates/`)

Extensions add new capabilities and commands; presets override how existing commands/templates render. Both are documented under `extensions/` and `presets/` with their own catalog JSON files.

### 4. Air-gapped install bundling

`pyproject.toml`'s `[tool.hatch.build.targets.wheel.force-include]` block copies `templates/`, `scripts/bash/`, `scripts/powershell/`, the bundled `extensions/git/`, `workflows/speckit/`, and `presets/lean/` into `src/specify_cli/core_pack/` at wheel-build time. This is what lets `specify init` work without network access. **If you add a new bundled asset (template, script, default extension/preset/workflow), add a force-include line — otherwise it ships only from the GitHub release zip and breaks enterprise/air-gapped users.**

### 5. Workflow engine (separate concern from CLI scaffolding)

`src/specify_cli/workflows/` is a YAML-driven, resumable step engine — orthogonal to the integration registry. `engine.py` dispatches step types from `workflows/steps/{command,shell,gate,if_then,switch,while_loop,do_while,fan_out,fan_in,prompt}/`. State persists between steps so runs survive interruption. See `workflows/ARCHITECTURE.md` for the execution model. Built-in workflow definitions live in `workflows/<name>/workflow.yml`.

### 6. CLI module layout

`src/specify_cli/__init__.py` is the Typer entry point (`specify = "specify_cli:main"`). Sibling modules split out concerns:

| File | Responsibility |
|---|---|
| `agents.py` | Agent listing/check helpers built on the registry |
| `extensions.py` | `specify extension {add,remove,list,search,info}` |
| `presets.py` | `specify preset {add,remove,list,search,info}` |
| `integration_runtime.py`, `integration_state.py` | `.specify/integration.json` state + per-install settings |
| `shared_infra.py` | Installs `.specify/scripts/`, `.specify/templates/` shared by all integrations |
| `_github_http.py` | Release ZIP fetching for non-bundled installs |

`__init__.py` is large (~5800 lines) by design — it owns user-facing Typer commands and rich UI. Don't refactor it without coordinating; CONTRIBUTING.md requires manual slash-command testing for any change touching CLI scaffolding.

## Working conventions

- **Project state files in user repos** live under `.specify/` (constitution, scripts, templates, integration state, installed extensions/presets). Spec artifacts live under `specs/<NNN>-<feature>/` (created by `/speckit.specify`).
- **Slash command naming**: `/speckit.<verb>` for command-mode integrations; `speckit-<verb>` skill name for skills mode (Codex always; Copilot via `--integration-options="--skills"`).
- **Branch naming for spec features**: `NNN-<feature-slug>` (auto-generated by `scripts/bash/create-new-feature.sh`). Tests in `tests/test_branch_numbering.py` and `tests/test_timestamp_branches.py` lock this in.
- **No `chore`/`docs` commit prefixes for `.claude/` directory edits** — global instruction from user CLAUDE.md.
- **AI-assisted contributions must be disclosed** in the PR (see CONTRIBUTING.md "AI contributions in Spec Kit").

## When changing agent integrations

1. Read `AGENTS.md` first — it has the full base-class decision tree, required fields, and a list of common pitfalls.
2. Run `uv run pytest tests/test_agent_config_consistency.py -q` — the fastest signal that wiring is intact.
3. Run the per-integration test: `uv run pytest tests/integrations/test_integration_<key>.py -v`.
4. Manual-test by `uv run specify init /tmp/x --integration <key>` and listing the produced command directory.
5. CONTRIBUTING.md "Determining which tests to run" has a prompt to derive the slash-command test matrix from your diff — paste it into your agent and include the output in the PR.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **spec-kit** (7146 symbols, 10193 relationships, 53 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/spec-kit/context` | Codebase overview, check index freshness |
| `gitnexus://repo/spec-kit/clusters` | All functional areas |
| `gitnexus://repo/spec-kit/processes` | All execution flows |
| `gitnexus://repo/spec-kit/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
