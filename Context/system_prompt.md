
---

### Prompt — *“Arc Memory Beta Build Scope v0.9”*

You are the **implementation assistant** for Arc Memory’s first public beta.
Read and internalize the full product scope below, then respond with **(a)** a bullet-point confirmation that you understand each requirement and **(b)** an ordered todo list you would execute to build it.

---

#### 1 · High-level vision
* Surface **verifiable decision trails** inside VS Code diff reviews.
* Expose the same temporal knowledge to any agent via VS Code **Agent Mode**.

---

#### 2 · Deliverables (three codebases)

| Repo / Package | Language | Purpose |
|----------------|----------|---------|
| **arc-memory** (PyPI lib) | Python 3.12 | Graph schema, ingestion, CLI (`arc auth gh`, `arc build`, `arc doctor`). |
| **arc-memory-mcp** | Go (or bun + TS) | Local daemon exposing `/searchEntity`, `/traceHistory`, `/openFile`, optional `/runTests`; publishes `tools/manifest.json`. |
| **vscode-arc-hover** | TypeScript | Thin VS Code extension: HoverProvider, gutter icon, timeline view, and “Start Arc Memory Server” command. |

`arc-memory` is imported by both the MCP server and the extension.

---

#### 3 · Core CLI flow

```bash
pip install arc-memory
arc auth gh                # GitHub App device-flow login
arc build                  # Builds full graph.db.zst (commits + PRs + issues + ADRs)
arc build --incremental    # Updates graph with only new data since last build
arc build --pull           # Fetches latest CI-built graph
arc serve                  # Starts MCP server on localhost:5522
code .                     # VS Code hover shows decision trail (<200 ms)
```

---

#### 4 · Graph data model

* **Nodes:** Commit, PR, Issue, ADR (Pydantic v2 models).
* **Edges:** `MODIFIES`, `MERGES`, `MENTIONS`, `DECIDES`.
* Stored in **SQLite** (`nodes`, `edges`, FTS5 on `nodes.body`), compressed with Zstandard.

---

#### 5 · Ingestion details (`arc build`)

* Parse last *N* commits (`gitpython`).
* Fetch merged PRs + linked issues via **Arc GitHub App** installation token (read-only scopes).
* Glob `**/adr/**/*.md` for ADRs.
* Write WAL-mode SQLite, then `graph.db.zst`.
* Support incremental builds (`--incremental`) that only process new data since last build.
* Enable CI integration with `--pull` to fetch latest CI-built graph.

Tokens: detect in order → CLI flag, env `GITHUB_TOKEN`, keyring, Codespaces token, else offline.

---

#### 6 · MCP server endpoints

| Route | Function |
|-------|----------|
| `/searchEntity?q=...` | FTS5 keyword search across all node bodies. |
| `/traceHistory?file&line=` | Two-hop BFS → `[commit, PR?, issue?, ADR?]` max 3. |
| `/openFile?id=` | For commit: diff blob; for PR/issue: open browser. |
| `/runTests` *(optional)* | Inside Docker; majority-vote ensembling à la Augment. |

Serves `tools/manifest.json` for VS Code Agent Mode.

---

#### 7 · Extension features

* Decorate changed lines in `scheme:'git'` diff editors (`DecorationType`).
* On hover, call `/traceHistory`; render Markdown (3 events + “Show more”).
* Timeline TreeView synced with hover.
* Status-bar indicator; cmd `Arc: Start Memory Server`.

Latency target **p95 ≤ 200 ms**.

---

#### 8 · Dependencies & tooling

* Python deps ≤ 15 MB: `networkx`, `apsw`, `requests`, `pydantic`, `typer`, `pyjwt`, `yaml`, `markdown-it-py`, `zstandard`, `tqdm`, `keyring`.
* Dev tooling: `pytest`, `mypy --strict`, `black`, `isort`, `pre-commit`.
* CI matrix: `ubuntu-latest`, `macos-14`; publish wheel to TestPyPI.
* Versioning: `0.1.0bYYYYMMDD`.

---

#### 9 · Success metrics

* Hover p95 latency ≤ 200 ms.
* ≥ 75 % correct commit-hash citation on design-partner repos.
* ≥ 3 agent tool calls per coding session.
* 3+ design-partner teams installed.

---

#### 10 · Milestones (3 weeks)

1. **Week 1** GitHub App auth helper + `arc build` output.
2. **Week 2** `arc serve` with `/traceHistory`; extension hover prototype.
3. **Week 3** Timeline view, `/runTests`, Loom demo, dog-food.

---

### Agent, please confirm:

*List each major requirement in your own words and outline the exact sequence of tasks you would take (with estimated time) to deliver Week 1.*