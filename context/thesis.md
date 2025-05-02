**Arc in one sentence**

*Arc is the local-first “what-if” engine for software: it captures the **why** behind every line of code, then simulates how new changes will ripple through your system **before** you hit Merge.*

---

### What Arc actually does

1. **Record the why.**  
   Arc’s Temporal Knowledge Graph ingests commits, PRs, issues, and ADRs to preserve architectural intent and decision history—entirely on the developer’s machine.

2. **Model the system.**  
   From that history Arc derives a **causal graph** of services, data flows, and constraints—a lightweight world-model that stays in sync with the codebase.

3. **Predict the blast-radius.**  
   A one-line CLI (`arc sim`) spins up an isolated sandbox, injects targeted chaos (network latency, CPU stress, etc.), and returns a risk score plus human-readable explanation for the current diff.

4. **Prove it.**  
   Every simulation writes a signed attestation that links input code, fault manifest, and metrics—auditable evidence that the change was tested under realistic failure modes.

---

### Why it matters

* **Catch outages before they exist.** Shift chaos left from staging to the developer’s laptop; trim MTTR and stop bad PRs at the gate.  
* **Trust AI suggestions.** Arc doesn’t just comment on code—it *proves* why a suggestion is safe (or isn’t) with sandbox data and a verifiable chain of custody.  
* **Local-first, privacy-first.** All graphs and simulations run inside a disposable E2B sandbox; no proprietary code leaves the developer’s environment.  
* **Built to extend.** The same graph and attestation layer will power live-telemetry world-models and multi-agent change control as teams grow.

---

**Arc = memory + simulation + proof—your safety net for the era of autonomous code.**