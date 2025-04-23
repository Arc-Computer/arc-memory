# Product Requirements Document (PRD)
**Product** Arc Memory — Python Package (v0.9)
**Scope note** This iteration focuses only on the Python package arc-memory. The MCP server (arc-memory-mcp) and VS Code extension (vscode-arc-hover) are subsequent milestones and are referenced here only for context.
**Authors** Jarrod Barnes & Core Engineering
**Last-updated** 23 Apr 2025

---

## 0 · Executive Summary
Arc Memory embeds a **local, bi-temporal knowledge graph (TKG)** in every developer’s workspace. It surfaces verifiable decision trails *in situ* during code-review and exposes the same provenance to any LLM-powered agent through VS Code’s new **Agent Mode**. The v0.9 beta must prove three things:

1. **Usefulness** — Reviewers answer “why did this change?” in \< 200 ms.
2. **Correctness** — ≥ 75 % of surfaced histories cite the right commit/PR/issue.
3. **Extensibility** — Agents (Cursor, Copilot, Windsurf) call Arc tools without glue.

The scope is intentionally narrow: GitHub repos, read-only permissions, local-first.

---

## 1 · Problem Statement
*AI systems are already generating > 25 % of new LOC at Google; 38 % of code-review comments require temporal reasoning over previous commits, bugs, or ADRs.*
Reviewers waste time hunting history; LLM agents re-introduce bugs because they lack provenance. Contemporary RAG solutions treat repos as flat text; long-context models are slow and hallucinate lineage. Arc fixes this with a local TKG and lightweight agent tools.

---

## 2 · Goals & Non-Goals

|  **In scope (Beta)**                 | **Out of scope (v1)**
|--------------------------------------|----------------------------------------------------|
| Local build of commit + PR + issue + ADR graph | GitLab, Bitbucket ingestion                |
| VS Code diff-hover & timeline UI     | IntelliJ / JetBrains plug-ins                       |
| Edge MCP server with 3(+1) endpoints | Cloud SaaS KG; multi-tenant hosting                 |
| GitHub App OAuth device-flow login   | Marketplace-listed GitHub App (private is enough)   |
| p95 hover latency ≤ 200 ms           | Interactive code-completion provider                |
| Optional Docker `/runTests` endpoint | Vector search (Chroma or other Vector DB)                               |

---

## 3 · Personas

| Persona | Pain | Desired outcome |
|---------|------|-----------------|
| **Staff+ Platform Engineer** (review gatekeeper) | Must understand *why* a change happened; digs through git log, PR comments, ADRs. | Hover a diff → see rationale in one glance. |
| **AI Agent (Copilot/Cursor)** | Lacks context; may undo previous security patch. | Call `/traceHistory` to guard against regressions. |
| **DevSecOps Lead** | Needs audit trail for SOC-2. | Arc stores provable links from diff → ADR/PR/Issue. |

---

## 4 · User Stories

1. *As a reviewer, when I hover a changed line, I see the last commit, the merged PR title, and any linked issue/ADR in < ¼ sec.*
2. *As an LLM agent, I can call `/searchEntity` “token expiry” and receive relevant commits and ADR IDs to avoid breaking auth.*
3. *As a CI engineer, I run `arc build` in GitHub Actions and attach `graph.db.zst` so every teammate has up-to-date history.*

---

## 5 · Functional Requirements

### 5.1 Graph Build (`arc build`)
* Parses up to **5 000** commits or **365** days, whichever first.
* Fetches **merged PRs** & linked **issues** via Arc GitHub App installation token (scopes: `contents:read`, `issues:read`, `pull_requests:read`).
* Globs `**/adr/**/*.md` for Architectural Decision Records.
* Outputs `graph.db` (SQLite + FTS5, WAL mode) then compresses to `graph.db.zst` (zstandard level 3).
* Creates manifest `build.json` with node/edge counts, timestamp, schema version.
* Supports incremental builds via `--incremental` flag to only process new data since last build.
* Tracks last processed commit hash, PR/issue IDs, and ADR modification times for efficient updates.

### 5.2 Python Package (`arc-memory`)
* Modules: `schema.py`, `ingest/git.py`, `ingest/github.py`, `ingest/adr.py`, `sql.py`, `cli/__init__.py`.
* Dependency budget ≤ 15 MB wheels.
* CLI commands via **Typer**:
  ```
  arc auth gh                # device-flow OAuth
  arc build                  # build full graph
  arc build --incremental    # update graph with new data only
  arc build --pull           # fetch latest CI-built graph
  arc doctor                 # validate db + print stats
  arc version
  ```
* Stores tokens in OS keychain via `keyring`; falls back to env var.

### 5.3 MCP Edge Server (`arc serve`)
* Static binary (Go) < 10 MB.
* Serves on UNIX socket or `localhost:<5522>`; Auth via `Bearer <nonce>`.
* Tools:

| Route | Description | Response example |
|-------|-------------|------------------|
| `/searchEntity` | FTS5 keyword search | `[{"id":"issue:456","title":"Revamp token expiry"}]` |
| `/traceHistory` | 2-hop BFS from file+line | `[{"type":"commit","id":"4f81..."}, {"type":"pr","id":"PR#342"}, {"type":"adr","id":"ADR-17"}]` |
| `/openFile` | commit → diff, PR/issue → browser URL | raw text or 302 redirect |
| `/runTests` (opt.) | run `pytest` inside Docker, majority vote | `{status:"pass", duration:42}` |

* Publishes `tools/manifest.json` for VS Code Agent Mode.

### 5.4 VS Code Extension (`vscode-arc-hover`)
* Activation events: `onGitDiffEditor`.
* `HoverProvider` for `scheme:'git'`; fetches `/traceHistory`.
* `DecorationType` gutter icon on changed lines.
* TreeView “Arc Memory” synced with hover.
* Command palette: `Arc: Start Memory Server`.
* p95 round-trip ≤ 200 ms (measured via telemetry).

---

## 6 · Non-Functional Requirements

| Quality | Target |
|---------|--------|
| **Performance** | Hover ≤ 200 ms; MCP CPU < 30 % on M1 Pro. |
| **Security** | All data local; tokens encrypted. |
| **Portability** | macOS ≥12, Ubuntu ≥20, Windows WSL. |
| **Installability** | One-liner pip; Homebrew for MCP; VSIX sideload. |
| **Observability** | Extension logs latency + success (opt-in). |
| **Test coverage** | Library ≥ 80 % line; server end-to-end tests. |

---

## 7 · Technical Design

### 7.1 Data Model
```python
class NodeType(str, Enum): COMMIT="commit"; PR="pr"; ISSUE="issue"; ADR="adr"
class CommitNode(BaseModel): id:str; msg:str; ts:datetime; files:list[str]
class EdgeRel(str, Enum): MODIFIES="MODIFIES"; MERGES="MERGES"; MENTIONS="MENTIONS"; DECIDES="DECIDES"
```

SQLite schema:
```sql
CREATE TABLE nodes(id TEXT PRIMARY KEY, type TEXT, title TEXT, body TEXT, extra JSON);
CREATE VIRTUAL TABLE fts_nodes USING fts5(body, content='nodes', content_rowid='id');
CREATE TABLE edges(src TEXT, dst TEXT, rel TEXT);
```

### 7.2 GitHub App Auth
* Arc registers one GitHub App (`Arc Memory`) with read-only scopes.
* CLI `arc auth gh` runs OAuth **device flow**; stores user token.
* `arc-build` signs JWT w/ private key → exchanges for installation token (1 h).

### 7.3 Ingestion Algorithm
1. `git log --reverse` → Commit nodes + `MODIFIES` edges.
   * For incremental: `git log <last_commit_hash>..HEAD` to get only new commits.
2. REST `/pulls` (state=merged) → PR nodes; link `MERGES`.
   * For incremental: Use `since=<last_build_timestamp>` parameter to fetch only updated PRs.
3. `/issues` + `/issues/:id/timeline` → Issue nodes; link `MENTIONS`.
   * For incremental: Use `since=<last_build_timestamp>` to fetch only new/updated issues.
4. Parse ADR Markdown → ADR nodes; `DECIDES` edges to files/commits.
   * For incremental: Only process ADRs with modification time > last build time.
5. Build NetworkX DiGraph in memory → write SQLite via APSW bulk inserts.
   * For incremental: Use transactions to add/update nodes without rebuilding entire graph.

### 7.4 Trace query (`/traceHistory`)
* Map file:line to commit via `git blame`.
* Follow `MERGES` ⇢ `PR`, then `PR` ⇢ `MENTIONS` ⇢ `Issue`, then `Issue` ⇢ inbound `DECIDES` ⇢ `ADR`.
* Return max 3 nodes, newest first.

### 7.5 CI Integration for Incremental Builds
* GitHub Actions workflow triggered on commits to main/master, PR creation/updates, and issue creation/updates.
* Workflow runs `arc build --incremental` to update the graph with only new data.
* Updated `graph.db.zst` is published as an artifact or committed back to the repository.
* Developers can run `arc build --pull` to fetch the latest CI-built graph.
* This ensures all team members have access to the most up-to-date knowledge graph without manual rebuilds.

---

## 8 · Milestones & Timeline

| Date | Milestone | Owner |
|------|-----------|-------|
| Apr 28 | GitHub App registered; `arc auth gh` MVP | Jarrod |
| Apr 30 | `arc build` commits + PR ingestion; tests pass | Eng 1 |
| May 3  | `arc serve` routes `/traceHistory`, `/searchEntity`; manifest validated | Eng 2 |
| May 6  | VSIX hover prototype w/ latency < 250 ms | Eng 3 |
| May 10 | Timeline TreeView; Docker `/runTests` harness | Eng 2 |
| May 12 | Internal dog-food on Arc repo; KPIs measured | All |
| May 14 | Loom walkthrough + docpack sent to 3 design partners | Jarrod |

---

## 9 · Open Questions

1. Should ADR parser support AsciiDoc?
2. Can we bundle a pre-built Docker image or ask users to provide one?
3. How many historical commits before hover latency degrades?
4. Error taxonomy finalized? (`GitHubAuthError`, `GraphBuildError`, …)

---

## 10 · Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| GitHub API rate-limits | Missing PR/issue nodes | Use installation token (5 k/hr) and incremental sync. |
| Large mono-repo graph (>100 MB) | Hover latency, memory | Slice to last N commits; background older shards. |
| Corporate proxy blocks OAuth flow | Onboarding friction | Provide PAT fallback in `arc auth gh`. |
| Users forget to run `arc build` | Stale graph | Add build-status banner in hover. |

---

## 11 · Analytics & Success Criteria

* **Hover latency** (telemetry) p95 ≤ 200 ms.
* **Citation accuracy** from manual QA on 5 design-partner PRs ≥ 75 %.
* **Agent tool usage** ≥ 3 calls / coding session.
* **Adoption** 3 partner teams with ≥ 5 active users each.

---

## 12 · Appendices

### A. ADR-001 (Architecture Decision)
*(link to `/docs/adr/ADR-001-Arc-Beta-Architecture.md`)*

### B. References
1. *Information Needs in Contemporary Code Review* (CSCW 2018) — 18 % rationale requests.
2. GitHub App authentication docs (JWT & installation token).
3. VS Code LanguageModelTool (MCP) spec.
4. Augment Code SWE-bench agent (OSS).

---

**End of PRD – v0.9**