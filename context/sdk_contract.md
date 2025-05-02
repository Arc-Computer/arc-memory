### `EXT-SDK-CONTRACT.md` · Arc Memory Extension ↔ SDK API **(frozen for v0.1)**

*Committed at `/docs/ext-sdk-contract.md`*

---

### 0. Purpose

This document is the single source of truth for how the VS Code extension talks to the Arc Memory SDK in **v0.1**.

Any change to payloads, flags, or return codes must be reflected here before code merges.

---

## 1 · Transport Options

| Mode | Default? | Lifecycle | Pros / Cons |
| --- | --- | --- | --- |
| **CLI + `--json`** | ✅ first implementation | Extension spawns `arc trace --json …` per request | Zero new code in SDK; +250 ms spawn latency |
| **Local RPC daemon** `arc rpc serve` | opt-in flag`"arc.rpc": "serve"` | Extension launches once, re-uses until VS Code exit | Near-zero latency; requires small FastAPI shim (see §7) |

Extension must detect if the daemon is listening on `127.0.0.1:32819`; else fall back to CLI.

---

## 2 · Version Handshake

*SDK prints at startup:* `ARC_RPC_PROTOCOL=1.0 SDK_VERSION=0.1.3`

Extension logs mismatch but continues if `PROTOCOL` major == 1.

---

## 3 · Methods / Commands

### 3.1 `trace` – rationale for a source location

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file_path` | string | ✓ | Absolute or `${workspaceRoot}`-relative POSIX path |
| `line` | int | ✓ | 1-based source line number |
| `max_events` | int |  | default `5` |
| `max_hops` | int |  | default `2` |

```
// TraceRequest
{
  "file_path": "src/auth/jwt.py",
  "line": 114,
  "max_events": 5,
  "max_hops": 2
}

```

```
// TraceResponse  (ordered newest➜oldest)
{
  "latency_ms": 92,
  "events": [
    {
      "id": "ADR-42",
      "kind": "ADR",
      "title": "Reduce JWT expiry to 900 s",
      "timestamp": "2025-04-24T18:03:11Z",
      "url": "file://docs/adr/042-jwt-expiry-900s.md",
      "summary": "Accepted decision to shorten session lifetime…"
    },
    {
      "id": "PR-298",
      "kind": "PullRequest",
      "title": "Refresh-token rotation support",
      "timestamp": "2025-04-23T22:11:31Z",
      "url": "https://github.com/acme/api/pull/298"
    }
    // …
  ]
}

```

### 3.2 `build` – full or incremental graph build

CLI: `arc build [--incremental] [--json]`

RPC: `POST /build { "mode": "incremental" }`

Return object:

```
{
  "status": "success",
  "duration_ms": 18423,
  "nodes_added": 242,
  "edges_added": 517
}

```

Exit code `0` = success, `1` = user error, `2` = internal error.

### 3.3 `adr.new` – generate ADR template (used by “+ Add Decision”)

CLI: `arc adr new --title "Reduce JWT expiry" --file docs/adr`

RPC: `POST /adr/new`

Request:

```json
{ "title": "Reduce JWT expiry to 900 s", "source_sha": "abc123" }

```

Response:

```
{
  "path": "docs/adr/2025-04-24-reduce-jwt-expiry.md",
  "status": "written",
  "stub_bytes": 813
}

```

---

## 4 · Exit codes (CLI mode)

| Code | Meaning | Extension action |
| --- | --- | --- |
| `0` | OK | normal handling |
| `10` | **Arc not initialised** (`graph.db` missing) | Prompt user to run `Arc: Build` |
| `20` | **Auth error** (`arc auth gh` not run) | Show login modal |
| `>0 other` | SDK failure | Show error toast, log telemetry |

---

## 5 · Telemetry Upload (opt-in pilots)

`POST /events` (daemon) or `arc telemetry push --file <jsonl>` (CLI).

Event schema lives in `/sdk/telemetry/schema.py`; extension mirrors in `telemetry/schema.ts`.

---

## 6 · JSON Schemas Sources of Truth

- Pydantic models → `arc_memory.rpc.schema`
- TypeScript types (generated via `quicktype`) → `src/rpc/types.ts`

---

## 7 · Minimal RPC shim (`arc rpc serve`)

*Port*: `32819` (configurable, env `ARC_RPC_PORT`)

*Endpoints*:

| Method | Path | Description |
| --- | --- | --- |
| GET | `/trace` | returns `TraceResponse` |
| POST | `/build` | kicks build |
| POST | `/adr/new` | create ADR stub |
| POST | `/events` | accept ND-JSON telemetry batch |

Implementation lives at `arc_memory/rpc/server.py`, ≤150 LoC FastAPI.

---

## 8 · Change-control

- PRs that alter this contract must:
    1. Update `PROTOCOL` version.
    2. Bump `sdkVersion` in extension’s `package.json`.
    3. Edit this file and get ✅ from both SDK & Extension maintainers.

---

*Frozen: 2025-04-24 · Maintainers: @jbarnes, @arc-memory-team*