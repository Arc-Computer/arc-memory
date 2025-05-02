Below is a **concrete folder-and-module map** that keeps the VS Code side thin, maximises testability, and draws a clean seam to the Python SDK.  It’s opinionated but mirrors patterns used in Sourcegraph’s `vscode-cody` and Graphite’s `vscode-graphite` repos, so new contributors will feel at home.

```
arc-vscode-extension/
├── package.json
├── tsconfig.json
├── webpack.config.js           # or esbuild config – bundle to <200 KB
├── src/
│   ├── extension.ts            # activation/cleanup, context keys
│   │
│   ├── rpc/                    # ▶ channel to Python
│   │   ├── RpcClient.ts        # start/stop child proc or connect to localhost:32819
│   │   └── types.ts            # TraceRequest, TraceResponse
│   │
│   ├── providers/
│   │   ├── HoverProvider.ts    # prefetch, render card, Ask-Arc flow
│   │   └── CodeLensProvider.ts # (future) “Show Decision Trail” lens
│   │
│   ├── views/
│   │   ├── TimelineWebview.ts  # side-panel HTML/JS
│   │   └── Templates.ts        # handlebars / lit templates
│   │
│   ├── commands/
│   │   ├── ExplainDiff.ts      # Arc: Explain This Diff
│   │   └── BuildGraph.ts       # Arc: Build / Rebuild
│   │
│   ├── agent/
│   │   ├── TraceTool.ts        # contrib tool for VS Code Agent-Mode
│   │   └── registry.ts         # registers with agent API
│   │
│   ├── telemetry/
│   │   ├── Telemetry.ts        # log -> JSON, debounce flush
│   │   └── schema.ts           # strongly-typed event enums
│   │
│   └── util/
│       ├── PrefetchQueue.ts    # per-file LRU of trace promises
│       └── Config.ts           # read ~/.arc/config
└── test/
    ├── hover.test.ts
    └── rpc.test.ts

```

---

## Runtime components & data flow

```
graph TD
    subgraph VS Code (Node/TS)
        A[HoverProvider] -->|prefetch| B(RpcClient)
        B --> C((arc rpc serve))
        A --> D[Telemetry]
        A --> E[Micro-prompt → Ollama]
        E -->|answer| A
        F[TimelineWebview] <-->|Open Timeline| A
        G[TraceTool] -.->|agent request| C
    end

    subgraph Local Python
        C -->|trace| H[SQLite graph.db]
        I[arc adr new] --> H
    end
```

- **RpcClient**: prefers `TCP localhost:32819`; falls back to `child_process spawn arc trace` if port closed.
- **PrefetchQueue**: fires on `onDidChangeTextEditorSelection` for visible ranges only; maintains 50-entry LRU.
- **Telemetry**: appends ND-JSON lines to `~/.arc/log/telemetry.jsonl` and flushes every 5 min (opt-in flag).

---

## Python side (inside SDK repo)

```bash
arc_memory/
├── rpc/
│   ├── __main__.py          # `python -m arc_memory.rpc` → start server
│   ├── server.py            # FastAPI / uvicorn  <100 lines
│   └── schema.py            # Pydantic models
├── cli/
│   └── adr.py               # `arc adr new` helper

```

- **Endpoints**
    - `GET /trace?file=<>&line=<>&hops=...` → JSON timeline (pre-serialised citations).
    - `POST /events` → receive extension telemetry (for opt-in pilots).

No graph-mutation needed for v0.1.

---

## Key architectural choices & why

| Choice | Reason |
| --- | --- |
| **Separate `rpc/` layer** | Keeps UI oblivious to Python process details; simplifies eventual remote-daemon swap. |
| **Webview for Timeline** | Isolates heavy HTML/JS; hover stays lightweight (<20 KB HTML). |
| **Local ND-JSON logs** | No network egress by default; eases partner privacy concerns. |
| **`arc adr new` helper** | Keeps ADR file-generation server-side; avoids duplicating templates in TS and Python. |

---

### Ready for implementation

With this scaffold the team can parallelise:

- **Extension UI** (providers, webview, commands).
- **RPC server** (tiny FastAPI).
- **ADR helper** in CLI.

Everything else—graph operations, trace algorithm—already lives in the SDK.

### Tiny tweaks to add

1. **Activation events**
    
    *Add `"onCommand:arc.build"` and `"workspaceContains:**/.git"` in `package.json` so the extension loads only when it can be useful.*
    
2. **Security headers for Webview**
    
    *Generate a nonce and set `Content-Security-Policy` that disallows remote scripts (required by guideline)[Visual Studio Code](https://code.visualstudio.com/api/ux-guidelines/webviews?utm_source=chatgpt.com).*
    
3. **Process recycling**
    
    *Use a singleton RpcClient to prevent multiple Python spawns; VS Code warns about orphaned processes in docs.*