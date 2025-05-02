## Resources for Implementing `arc sim`

This file collects **all external references, code snippets, and schemas** your coding agent will need. Everything else (repo paths, sample data) already lives inside the Arc Memory workspace.

---

### 1. Orchestration — LangGraph

| Item | Link / Note |
|------|-------------|
| LangGraph landing & concepts |  ([LangGraph - LangChain](https://www.langchain.com/langgraph?utm_source=chatgpt.com)) |
| Blog post with multi-agent workflow example (shows state-passing) |  ([LangGraph: Multi-Agent Workflows - LangChain Blog](https://blog.langchain.dev/langgraph-multi-agent-workflows/?utm_source=chatgpt.com)) |

---

### 2. CLI Framework — Typer

| Item | Link |
|------|------|
| Sub-command (command-group) patterns you must follow |  ([SubCommands - Command Groups - Typer](https://typer.tiangolo.com/tutorial/subcommands/?utm_source=chatgpt.com)) |

---

### 3. Git & Diff Handling

| Item | Link |
|------|------|
| Using **GitPython** to compute and iterate diffs |  ([python - gitpython and git diff - Stack Overflow](https://stackoverflow.com/questions/20061898/gitpython-and-git-diff?utm_source=chatgpt.com)) |

---

### 4. Sandbox Runtime

| Item | Link / Note |
|------|-------------|
| E2B SDK cookbook repo (Python examples, `run()` API) |  ([e2b-dev/e2b-cookbook: Examples of using E2B - GitHub](https://github.com/e2b-dev/e2b-cookbook?utm_source=chatgpt.com)) |
| Quick-start for custom sandbox images & package install |  ([Install custom packages - E2B - Code Interpreting for AI apps](https://e2b.dev/docs/quickstart/install-custom-packages?utm_source=chatgpt.com)) |

---

### 5. Lightweight Kubernetes

| Item | Link |
|------|------|
| `k3d cluster create` command reference |  ([K3d cluster create](https://k3d.io/v5.3.0/usage/commands/k3d_cluster_create/?utm_source=chatgpt.com)) |
| k3d quick-start cheat-sheet |  ([k3d](https://k3d.io/?utm_source=chatgpt.com)) |

---

### 6. Fault Injection

| Item | Link / Snippet |
|------|----------------|
| Chaos Mesh docs — creating any experiment |  ([Run a Chaos Experiment](https://chaos-mesh.org/docs/run-a-chaos-experiment/?utm_source=chatgpt.com)) |
| **Minimal `NetworkChaos` (250 ms delay) YAML**  

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  selector:
    namespaces: ['default']
    labelSelectors:
      'app': payments-svc
  mode: one
  action: delay
  delay:
    latency: '250ms'
  duration: '60s'
  direction: to
``` |

---

### 7. Metric Collection

| Item | Link |
|------|------|
| Prometheus Python client—quick counter/gauge/histogram example |  ([Python Monitoring with Prometheus (Beginner's Guide) - Better Stack](https://betterstack.com/community/guides/monitoring/prometheus-python-metrics/?utm_source=chatgpt.com)) |

---

### 8. Code-style / Lint Config

| Tool | Link / Note |
|------|-------------|
| **Black** — where it reads `pyproject.toml` |  ([The basics - Black 25.1.0 documentation](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html?utm_source=chatgpt.com)) |
| **Ruff** configuration guide |  ([Configuring Ruff - Astral Docs](https://docs.astral.sh/ruff/configuration/?utm_source=chatgpt.com)) |

---

### 9. Attestation Reference

| Item | Link |
|------|------|
| Sigstore example JSON attestation & policy |  ([Sample Policies - Sigstore](https://docs.sigstore.dev/policy-controller/sample-policies/?utm_source=chatgpt.com)) |

> **Schema hint**  
> Your attestation JSON should, at minimum, include:  
> `sim_id`, `manifest_hash`, `commit_target`, `metrics`, `timestamp`, and the raw `diff_hash`.

---

### 10. Sample Commands / Templates (ready to paste)

| Purpose | Snippet |
|---------|---------|
| **Spin a sandbox cluster** | `k3d cluster create arc-sim --image rancher/k3s:v1.29.0-k3s1 --servers 1 --agents 0` |
| **Install Chaos Mesh** | `helm repo add chaos-mesh https://charts.chaos-mesh.org && helm install chaos-mesh chaos-mesh/chaos-mesh --namespace chaos-testing --create-namespace --set chaosDaemon.runtime=docker` |
| **Invoke E2B** (Python) | ```python\nimport e2b\nrun = e2b.run(image='arc-sim:latest', script='bootstrap.sh', timeout=600)\n``` |

---

### 11. Internal Repo Pointers (no external links)

| Path | What it gives you |
|------|-------------------|
| `arc_memory/cli/__init__.py` | Typer app instance (`app = Typer()`)—extend here. |
| `arc_memory/cli/trace.py` | Pattern for diff serialization & JSON output. |
| `sql/db.py`, `schema/models.py` | Graph store access and Node/Edge models (use in `derive_causal()`). |
| `.pre-commit-config.yaml`, `.ruff.toml`, `pyproject.toml` | Style & lint settings—keep new code compliant. |
| `sample-repos/lotus-demo` | Small repo + ready diff for unit tests. |
