# VS Code Extension — Product Strategy Doc

> Purpose: Translate Arc Memory’s "wow‑moment" hover experience into an actionable design & engineering plan for an MVP VS Code extension, built on top of the existing SDK.
> 

---

## Problem Statement

Developers spend excessive time hunting for *why* a change exists. Existing AI assistants surface code context, but the historical rationale remains buried across PRs, Slack, and ADRs ("decision amnesia"). Arc’s SDK already builds a local temporal knowledge graph that can answer "why" queries in <200 ms but that power is trapped in the CLI.

## Strategic Opportunity

- "Diff is the new control‑loop" for engineers. Surfacing rationale inline—in the diff—creates a uniquely sticky interface that complements Sourcegraph/Cody, Graphite stacked‑PRs, and Cursor/Windsurf chat patterns without competing on code‑generation.
- Fast, provenance‑rich context (<500 ms) differentiates us from Cody (~1 s+ cold latency).
- Local‑first privacy is a selling point vs. cloud‑first tools.

## Goals & Success Metrics

| Objective | KPI | Target (MVP) |
| --- | --- | --- |
| Deliver "aha" hover card | Time‑to‑first‑paint | **< 500 ms** on mid‑sized repo |
| Drive usage | Hover‑card open rate | **> 60 %** of changed hunks |
| Prove depth | Card dwell ≥2 s | **> 40 %** of opens |
| Validate conversation loop | Follow‑up prompt / hover | **≥ 1 per 5** |
| Capture decisions | New decision records added | Baseline > 0.2 / dev / day |

## Wow Moment – Definition

*While reviewing a diff, a developer hovers a changed line and—within 0.5 s—sees a card that narrates the decision trail (Slack → ADR → PR) with tappable citations and a “Ask Arc” follow‑up prompt.*

## User Personas & Journeys

1. **Staff Engineer Sarah (IC)** – cares about quickly understanding unfamiliar code during review.
2. **Team Lead Leo (Reviewer)** – evaluates multi‑stacked PRs, needs confidence before approve.
3. **AI‑Augmented Power‑User Priya** – uses Cursor Agent‑Mode and wants deep context for generated refactors.

### Key Journey (Sarah)

| Step | Sarah’s action | Extension behaviour | SDK / repo effect |
| --- | --- | --- | --- |
| **0. Install** | `pip install arc-memory` → installs extension from marketplace | On first run checks for `arc` CLI & prompts `arc auth gh` if missing | — |
| **1. Build graph** | `arc build` (CLI or status-bar button) | Shows progress toast; spawns SDK build | Local SQLite TKG built |
| **2. Review diff** | Opens PR #5 in VS Code | Prefetches `trace(file, line)` for each changed hunk (<100 ms each) | No change |
| **3. Hover** | Hovers `token_expiry = 900` line | Card pops < 500 ms with: timeline of Slack, ADR #42, PR 298; buttons **Ask Arc**, **Add Decision** | Reads graph only |
| **4-a. Ask Arc** | Clicks **Ask Arc** → types “Were other expiries considered?” | Extension calls SDK trace, pipes nodes to local Ollama model (e.g. Gemma 3) → returns 2-sentence answer with citations | — |
| **4-b. Capture decision** | Clicks **Add Decision** | Presents dropdown:• **AI-draft ADR** (default)• **Manual entry** | — |
| → AI draft flow | Picks AI-draft | Extension sends diff context + trace notes to Ollama → renders Markdown ADR stub; shows preview; Sarah hits **Save** | Writes `docs/adr/2025-04-…-token-expiry.md` to repo |
| → Manual flow | Picks Manual | Opens empty ADR template in split editor | Same file written manually |
| **5. Commit / merge** | Sarah pushes ADR or merges PR | CI runs `arc build --incremental`; ADR ingested automatically | Graph now carries decision |

## Competitive Landscape & Differentiation

| Tool | Strength | Weakness | Arc Edge |
| --- | --- | --- | --- |
| Sourcegraph Cody | Rich code intel | 800‑1200 ms hover latency; fuzzy embeddings | 100 µs graph query & full provenance |
| Graphite stacked PRs | Reduces diff size & review pain | No historical rationale overlay | Complements with rationale per stack step |
| Cursor / Windsurf | Inline AI chat | Rationale shallow, sidebar heavy | Inline, citation‑first “why” & follow‑up prompt |

## Functional Scope (MVP v0.1)

- **Inline Affordance** – gutter dot on changed lines with pre-fetched memory.
- **Hover Card** – < 500 ms; 3-5-event timeline, citations, micro-prompt (`Ask Arc`), `Open Timeline`.
- **Decision-Trail Side Panel** – expandable view; `+ Add Decision` with AI-draft / Manual option → writes Markdown ADR.
- **Command Palette / Agent Hooks** – `Arc: Explain This Diff`; status-bar **Build** button; expose `arc.memory.trace` tool for Agent-Mode.
- **Instrumentation** – local logs: build success/time, hover open & latency, card dwell, micro-prompt submit, ADR-draft accepted.

## Non‑Functional Requirements

- **Latency:** < 500 ms card paint, 95‑th pctl.
- **Accuracy:** decision trail precision ≥ 95 %; every item cites source.
- **Privacy:** default local‑only; MCP opt‑in later.
- **Resource:** memory overhead <50 MB extension; CPU idle.

## Implementation Phases

| Sprint | Deliverables |
| --- | --- |
| **0** | Spike hover provider + fake data; latency benchmark |
| **1** | Wire to SDK (`arc.trace`) & caching; simple card; metrics logging |
| **2** | Side‑panel timeline & Add‑Decision form; Ask Arc prompt ↔ SDK natural language wrapper |
| **3** | Polishing: icons, keyboard nav, privacy badge; internal dogfood & partner rollout |

## Telemetry & Analytics Plan

- `hover_open` (timestamp, latency)
- `hover_dwell` (ms)
- `ask_arc_query` (chars, diff_id)
- `decision_added` (char_count)
- Local JSON ring‑buffer → optional anonymized upload on opt‑in.

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Hover latency regression | Prefetch + LRU cache; CI perf tests |
| Low wow‑moment recall | Surveys in extension panel; iterate content density |
| Privacy concerns | Keep everything local; clear status badge |
| SDK query errors | Fallback banner & diagnostic command `Arc: Doctor` |
- **LLM usage in v0.1**
    1. **Ask Arc** – micro-prompt inside the hover card (2-sentence answer with citations).
    2. **AI-draft ADR** – fills the Markdown template when the user clicks **+ Add Decision**.

Everything else (hover timeline, citations, side-panel) is graph-only—no generation.

## Open Questions

1. Decision capture schema – leverage ADR template in repo or store as JSON in graph only?
2. When to surface PR‑badge integration with GitHub—pre or post‑MVP?

## Storyboard

---

## One-time install flow

| Phase | UX we show | Behind the scenes | Push-back / rationale |
| --- | --- | --- | --- |
| **A. Extension install** | VS Code Marketplace → *Arc Memory* | — | ✅ |
| **B. Prereq check** | Modal: “Arc needs the `arc` CLI (100 KB) & Python 3.10+. Click **Install & Build**.” | • Downloads `pip` wheel inside venv.• Runs `arc auth gh` → pops GitHub device-code screen.• Kicks off `arc build` (shows progress). | *Don’t ask user to copy CLI commands.* One click = lower drop-off. |
| **C. Optional LLM** | After build: “Want AI answers & ADR drafts? Click **Enable AI**, pulls ~1 GB model via Ollama.”Button **Skip for now**. | If enabled, `ollama pull phi3:mini` in a subprocess; store flag `aiEnabled=true`. | Optional keeps privacy-conscious teams happy; no hard block on aha moment. |

**Result:** Workspace now has a built graph; Sarah can open any diff immediately.

---

## First “wow” inside a PR review

1. **Sarah opens PR #5** → extension pre-fetches `trace()` for each modified hunk.
2. **Hovers** a changed `token_expiry` line → < 500 ms card shows 3-event timeline + citations + micro-prompt field.
3. Types **“Were other expiries considered?”** → if AI enabled, local model streams 2-sentence answer with citations; otherwise tooltip: *“Enable AI for answers”*.

> Aha moment: verifiable rationale appears where her eyes already are; optional follow-up proves depth.
> 

---

## Decision capture after merge

| Trigger | UX | Behaviour | Notes |
| --- | --- | --- | --- |
| **PR merged** *or* large commit | Toast: **“Capture decision rationale?”** Buttons → **AI-draft ADR** / **Manual** / **Later** | If AI enabled & clicked: generate Markdown stub via local model, open editor for review → save under `docs/adr/YYYY-MM-slug.md`.Manual opens empty template. | Gentle nudge, not modal – avoids blocking CI merge gates. |
| **Next `arc build`** (CI or local) | — | ADR ingested → rationale now surfaces on hovers for future diffs. | No live graph mutation needed in v0.1. |

---

## Instrumentation checklist (what to log)

| Event | Fields |
| --- | --- |
| **build-start / build-end** | repo hash, duration, success |
| **hover-open** | file, line, cache-hit, t_load |
| **hover-close** | dwell_ms |
| **ask-arc** | chars_in, t_first_token, total_tokens |
| **timeline-open** | file, line |
| **adr-draft-opened / accepted / cancelled** | ai_draft bool, bytes_written |
| **extension heartbeat** | daily to count active devs |

These are the KPIs we’ll show design partners and investors to prove daily pull.

---

## Why this journey is tight enough

- **Zero terminal copy-pasta** – one click install mirrors Copilot’s onboarding conversion lessons.
- **Aha before AI** – provenance alone delivers value; AI is an enhancer, not a blocker.
- **No ghost-text assist** – avoids overlap with Copilot, keeps focus on diff review.
- **ADR prompt at merge, not on hover** – separates thinking (review) from documentation (decision), matching engineers’ mental model.
- **All heavy work in SDK** – extension remains a thin UI + RPC client; only tiny addition is the optional `Enable AI` pull helper.

---

**Ownership**

*PM:* Jarrod Barnes

*Design:* TBD

*Engineering:* Jarrod Barnes

**Target MVP Ship:**  *Four weeks from sprint‑0 kickoff.*

## Data that matters

## Outcome KPIs — value & monetisation evidence

| Outcome | Measurement | Reference benchmark |
| --- | --- | --- |
| **Review time saved** | Median minutes per PR review (self-report) ↓ 20 % | Graphite claims stacked PRs cut review times ≥ 25 %[Graphite.dev](https://graphite.dev/blog/stacked-prs?utm_source=chatgpt.com) |
| **Bug-fix lookup time** | “Minutes to trace decision” survey vs. baseline ↓ 50 % | Sourcegraph positions code-search to halve search time; your memory should beat that[Sourcegraph](https://sourcegraph.com/blog/the-future-of-code-search?utm_source=chatgpt.com) |
| **Pilot NPS** | ≥ +30 after 3 weeks | Copilot research links NPS uptick to > 5 min/day time saved[The GitHub Blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/?utm_source=chatgpt.com) |
| **Willingness-to-pay score** | ≥ 15/20 on your hair-on-fire rubric | Aligns with your discovery scoring table |

## Support KPIs — health & performance signals

| Category | Metric | Target | Competitive pattern |
| --- | --- | --- | --- |
| **Activation** | Install ➞ first-build success | **> 80 %** complete in < 3 min | VS Code flags extension activation friction ≥ 30 % as a warning[Visual Studio Code](https://code.visualstudio.com/docs/configure/telemetry?utm_source=chatgpt.com) |
|  | Install ➞ first-hover elapsed time | **≤ 5 min** | GitHub Copilot emphasises “5-min time-to-first-suggestion” internal OKR[The GitHub Blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/?utm_source=chatgpt.com) |
| **Reliability** | Trace cache–hit rate | **≥ 70 %** | Keeps successive hovers < 200 ms p95 |
| **LLM perf** *(if AI enabled)* | Phi-3 response latency p95 | **< 300 ms** | Developer satisfaction drops sharply > 700 ms in AI-completion latency study[Medium](https://medium.com/%40adnanmasood/rethinking-developer-productivity-in-the-age-of-ai-metrics-that-actually-matter-61834691c76e?utm_source=chatgpt.com) |
| **Usage retention** | Weekly Active Dev / Installed Dev | **> 40 %** after week 1 | Copilot DAU/MAU settles around 40–50 % in internal reports[Medium](https://medium.com/%40adnanmasood/why-your-development-team-should-embrace-ai-coding-tools-and-how-to-measure-their-impact-8ca92863da58?utm_source=chatgpt.com) |

## Core “Aha” KPIs — prove the hover-wow loop

| Metric | Target (pilot) | Why it matters | Competitive signal |
| --- | --- | --- | --- |
| **T-first-hover latency (p95)** | **< 500 ms** | Anything slower erodes trust; Cody added latency buckets after user complaints[Sourcegraph](https://sourcegraph.com/docs/technical-changelog?utm_source=chatgpt.com) | Sourcegraph bucketises completions to watch sub-800 ms SLA[Sourcegraph](https://sourcegraph.com/docs/technical-changelog?utm_source=chatgpt.com) |
| **Hover open rate / changed hunk** | **≥ 60 %** | Mirrors stacked-PR link-click rates that Graphite cites for “view previous” events[Graphite.dev](https://graphite.dev/blog/stacked-prs?utm_source=chatgpt.com) | Shows devs notice the dot and consider it valuable |
| **Hover dwell ≥ 2 s** | **≥ 40 % of opens** | Longer reads correlate with perceived relevance in Copilot Chat studies[The GitHub Blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-code-quality/?utm_source=chatgpt.com) |  |
| **Ask-Arc prompt usage** | **1 per 5 hovers** | Proves devs want deeper context, not just passive read | Copilot & Cursor both instrument chat-per-file; see Copilot productivity study notes[The GitHub Blog](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/?utm_source=chatgpt.com) |
| **Decision-capture conversion***(ADR draft accepted or manual)* | **≥ 30 % of merge prompts** | Validates that Arc not only reads memory but helps create it | No direct analog—differentiator vs. Sourcegraph & Graphite |

## Qualitative hooks

- **Weekly 15-min usability call** → Record screens
- **3-question pulse survey inside VS Code** (Was this context helpful? Y/N, What was missing? free-text).

Track *latency → engagement → decision capture* as the core loop, with retention and time-saved as outcome proof