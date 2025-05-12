# Arc Memory – Shared Context for Phase 1 OSS Development

**Last updated:** {{DATE}}

---

## Purpose

This document gives every contributor —including AI coding agents — a single *source of truth* for Phase 1 of the Arc Memory roadmap. It explains **what** we’re building, **why** it matters, **where** each feature lives (worktree/branch), and **how** to collaborate without breaking the main code line.

*Keep this doc short, precise, and always up‑to‑date. If you change a core assumption or interface, edit this file in the same PR.*

---

## TL;DR of Phase 1

| Feature            | Goal                                                                                  | Branch / Worktree                                    | Status Flag |
| ------------------ | ------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------- |
| **Auto‑Refresh**   | Keep local knowledge‑graph fresh on a schedule; lay foundation for incremental ingest | `feature/auto-refresh` ( `../arc-auto-refresh` )     | `IN DEV`    |
| **SDK Refactor**   | Expose Arc APIs as a clean Python package + plugin interface; enable agent frameworks | `feature/sdk-refactor` ( `../arc-sdk-refactor` )     | `IN DEV`    |
| **CI Integration** | Provide blast‑radius + provenance checks in PR via GitHub Actions                     | `feature/ci-integration` ( `../arc-ci-integration` ) | `IN DEV`    |

All three depend on the shared **`arc_memory`** core. Phase 1 targets an *OSS* release (tag `v0.5.0`) that delights open‑source maintainers. Cloud work begins **after** these merge into `main`.

---

## Branch & Worktree Conventions

> We use **Git worktrees** so each feature evolves in isolation while staying in the same repo history.

```bash
# example setup
git checkout main && git pull
# auto‑refresh worktree
git worktree add ../arc-auto-refresh feature/auto-refresh
# sdk refactor worktree
git worktree add ../arc-sdk-refactor feature/sdk-refactor
# ci integration worktree
git worktree add ../arc-ci-integration feature/ci-integration
```

* **One feature, one branch, one worktree**. Don’t mix tasks.
* Keep a dedicated worktree for `main` (`../arc-main`) and rebase your feature branch onto `main` at least **daily**.
* Remove a worktree (`git worktree remove …`) after the branch merges.

---

## Core Architectural Contracts

### `arc_memory` Package

* **Single entry‑point:** `arc_memory.core` exposes stable APIs used by CLI, SDK, and CI.
* **DB Abstraction Layer**: `arc_memory.db` must support `SQLite` **and** future `Neo4j` back‑ends via the adapter pattern.

  * Do **not** import `sqlite3` or the Neo4j driver directly outside adapter modules.
* **Plugin Interface**: new plugins inherit from `arc_memory.plugins.BasePlugin` and are registered via `arc_memory.plugins.registry`.
* **Backwards‑compat:** Until `v1.0`, breaking API changes require `@deprecated` wrapper + upgrade note in `CHANGELOG.md`.

### Feature Flags

Every new capability ships **off by default**:

```bash
# ~/.arc/config.toml
[features]
auto_refresh = true
sdk_v2       = false  # set true for experimental SDK refactor
ci_checks    = false
```

Flags live in `arc_memory.config.features` and are read by CLI & CI.

### Coding Standards

* **Python ≥ 3.10**; lint with `ruff`, format with `black`.
* **TypeScript ≥ 5.4**; lint with `eslint`.
* All public functions/classes → docstrings + type hints.
* Use **commit messages**:
  `feat(auto-refresh): human‑readable summary \n\nWHY: <rationale>`

---

## Feature‑Specific Expectations

### 1 · Auto‑Refresh (`feature/auto-refresh`)

* ✔ New CLI command: `arc refresh` (manual) & background scheduler (`arc‑agent --refresh`).
* ✔ Incremental ingest based on git commit SHAs.
* ✔ Configurable cadence (default daily) via `~/.arc/config.toml`.
* ✘ Do **not** yet integrate Neo4j; stub adapter but leave behind feature flag.
* Tests: `tests/refresh/` must pass in isolation; use mocked repo.

### 2 · SDK Refactor (`feature/sdk-refactor`)

* ✔ Export stable public surface in `arc_memory.sdk.*` (functions ✚ dataclasses).
* ✔ Introduce plugin scaffold + first reference adapter (LangChain Tool).
* ✔ Retain existing CLI by delegating to new APIs (no user‑visible breakage).
* ✘ No async rewrite yet; plan but keep sync wrappers.
* Tests: `tests/sdk/` verify old and new APIs both return identical results on sample graph.

### 3 · CI Integration (`feature/ci-integration`)

* ✔ GitHub Action `arc-ci.yml` that runs `arc ci-check` on PR.
* ✔ Comment template includes blast‑radius section + related issues.
* ✔ Must run ≤ 60 seconds on medium repo.
* ✘ RL outcome model is **out‑of‑scope**; use heuristic dependency walker.

---

## Testing & Continuous Integration

* GitHub Actions workflows:

  * `ci.yml` → triggered on *all* branches; runs lint + unit tests matrix (Py 3.10–3.12, Node 18–20).
  * `integration-nightly.yml` → merges latest feature branches into a temp branch; runs full test suite.
* Coverage target ≥ 85 % for `arc_memory` core.
* Failing tests block merge to `main`.

---

## Merging & Release Flow

1. **Finish feature branch** → open PR to `main`.
2. Automated checks → green. Manual review → ensure *WHY* is documented.
3. If major API changes: update `AGENT_SHARED_CONTEXT.md`, `CHANGELOG.md`, & bump `arc_memory.__version__`.
4. Merge → tag pre‑release (e.g. `v0.3.0‑auto-refresh-alpha`) via CI.
5. Repeat until all Phase 1 features are merged. Then cut `v0.3.0`.

---

## Communication & Knowledge Graph

* All architectural decisions land in `docs/adr/*.md` (Arc will ingest ADRs automatically).
* Use GitHub Discussions for questions; label `#sdk`, `#ci`, `#refresh`.
* The *Arc Memory (self)* demo repo showcases our own commit history as a knowledge graph—agents can query `arc why <file>` to understand past decisions.

---

## Quick Reference Cheatsheet

```bash
# list worktrees
git worktree list
# sync feature branch with main
git fetch origin && git rebase origin/main
# run tests for current worktree
pytest -q
# run full lint
task lint
```

---

*Build fast, break nothing, document **why**.*
