# Implementation Plan: `arc sim` Command

## Overview

This document outlines the implementation plan for the new `arc sim` CLI command in Arc Memory. The `arc sim` command will enable simulation-based impact prediction by analyzing code diffs, running targeted fault injection experiments in isolated sandbox environments, and providing risk assessments with attestation.

## 1. Goals and Success Criteria

### Primary Goal
Design and ship a Typer sub-command `arc sim` that runs a "network_latency" simulation end-to-end and outputs a risk JSON file—all in ≤15 min wall-clock on a developer laptop.

### Success Criteria
1. The `arc sim` command can analyze a diff and identify affected services
2. It can spin up a sandbox environment and inject a network latency fault
3. It can collect simple metrics and determine a risk score
4. It generates a clear explanation of potential impacts
5. All tests pass and the command integrates with the existing Arc Memory CLI

## 2. Command Interface

```bash
arc sim [OPTIONS]

Required:
  --range TEXT         Git rev-range   (default: HEAD~1..HEAD)
                       OR
  --diff PATH          Pre-serialized diff JSON

Options:
  --scenario TEXT      Fault scenario ID (default: network_latency)
  --severity INT       CI fail threshold 0-100  (default: 50)
  --timeout INT        Max runtime sec   (default: 600)
  --output PATH        Write result JSON (default: stdout)
  --open-ui / --no-ui  Open VS Code webview if available (default: no-ui)
  -v, --verbose
```

### Exit Codes
- `0`: Success - Simulation completed successfully with risk score below severity threshold
- `1`: Failure - Simulation completed but risk score exceeds severity threshold
- `2`: Error - Simulation failed to complete due to technical issues
- `3`: Invalid Input - Command arguments are invalid or missing

### Output JSON Schema
```json
{
  "sim_id": "string",
  "risk_score": 0-100,
  "services": ["service1", "service2"],
  "metrics": {
    "latency_ms": 250,
    "error_rate": 0.05
  },
  "explanation": "string",
  "manifest_hash": "string",
  "commit_target": "string",
  "timestamp": "ISO-8601 timestamp",
  "diff_hash": "string"
}
```

## 3. Implementation Steps

### Step 1: Set Up Command Structure
1. Create a new file `arc_memory/cli/sim.py` for the `arc sim` command
2. Define the Typer app and command structure following existing patterns
3. Register the command in `arc_memory/cli/__init__.py`
4. Implement basic argument parsing and validation

### Step 2: Implement Diff Analysis
1. Create a module for diff handling using GitPython
2. Implement functions to:
   - Extract diff from Git using the provided rev-range (`serialize_diff(range:str)->dict`)
   - Parse pre-serialized diff JSON if provided
   - Identify affected files and services (`analyze_diff(diff:dict, causal_db:str)->list[str]`)
   - Reuse existing patterns from `cli/trace.py` where applicable

### Step 3: Derive Static Causal Graph
1. Create a module for causal graph derivation
2. Implement functions to:
   - Extract a Static Causal Graph (SCG) from Arc's Temporal Knowledge Graph (`derive_causal(db_path:str)->None`)
   - Map changed files to system components using the SCG
   - Identify potential impact paths

### Step 4: Create Simulation Manifest Generator
1. Create a module for generating simulation manifests
2. Implement functions to:
   - Define fault scenarios (starting with network_latency)
   - Generate YAML manifests for Chaos Mesh experiments
   - Configure the simulation environment

### Step 5: Implement Sandbox Environment
1. Create modules for sandbox environment management
2. Implement functions to:
   - Initialize E2B sandbox environments
   - Set up k3d clusters inside the sandbox
   - Deploy Chaos Mesh for fault injection
   - Clean up resources after simulation

### Step 6: Implement Fault Injection
1. Create a module for fault injection
2. Implement functions to:
   - Apply network latency faults using Chaos Mesh
   - Monitor the system during fault injection
   - Collect metrics and logs

### Step 7: Implement LangGraph Workflow
1. Create a module for orchestrating the simulation workflow
2. Implement functions to:
   - Define the workflow steps
   - Handle state passing between steps
   - Manage the overall simulation process

### Step 8: Implement Results Analysis and Attestation
1. Create modules for analyzing simulation results and generating attestation
2. Implement functions to:
   - Process collected metrics
   - Calculate risk scores
   - Generate human-readable explanations
   - Create attestation JSON with cryptographic verification

### Step 9: Add Tests
1. Create unit tests for each module
2. Create integration tests for the full workflow
3. Create test fixtures and mocks for E2B and Chaos Mesh

### Step 10: Add Documentation
1. Create CLI documentation in `docs/cli/sim.md`
2. Update README.md to include the new command
3. Add examples in `docs/examples/simulation.md`

## 4. Module Structure

```bash
arc_memory/
├── cli/
│   ├── __init__.py (updated to include sim command)
│   └── sim.py (new file for sim command)
├── simulate/
│   ├── __init__.py
│   ├── diff_utils.py (diff analysis)
│   ├── causal.py (causal graph derivation)
│   ├── manifest.py (simulation manifest generation)
│   ├── e2b_runtime.py (E2B wrapper)
│   ├── sandbox.py (high-level sandbox management)
│   ├── fault_driver.py (fault injection)
│   ├── explanation.py (results analysis)
│   ├── langgraph_flow.py (workflow orchestration)
│   └── mocks.py (test mocks for E2B and Chaos Mesh)
├── attestation/
│   └── write_attest.py (attestation generation)
└── tests/
    ├── unit/
    │   ├── simulate/
    │   │   ├── test_diff_utils.py
    │   │   ├── test_causal.py
    │   │   ├── test_manifest.py
    │   │   ├── test_e2b_runtime.py
    │   │   ├── test_sandbox.py
    │   │   ├── test_fault_driver.py
    │   │   ├── test_explanation.py
    │   │   └── test_langgraph_flow.py
    │   └── attestation/
    │       └── test_write_attest.py
    └── integration/
        └── test_sim_command.py
```

## 5. Dependencies

1. **LangGraph** - For orchestrating the simulation workflow
2. **E2B** - For providing isolated sandbox environments
3. **GitPython** - For computing and iterating diffs
4. **PyYAML** - For generating YAML manifests
5. **Typer** - For CLI command structure
6. **Rich** - For console output formatting

## 6. Implementation Details

### 6.1 Diff Analysis (`diff_utils.py`)
- Use GitPython to compute diffs between commits
- Implement `serialize_diff(rev_range:str)->dict` to extract diff from Git
- Implement `analyze_diff(diff:dict, causal_db:str)->list[str]` to identify affected services
- Include timestamp in serialized diff output for consistent data across modules
- Reuse patterns from `cli/trace.py` where applicable

### 6.2 Causal Graph Derivation (`causal.py`)
- Implement `derive_causal(db_path:str)->None` to extract relationships from the TKG
- Build a directed graph of service dependencies
- Identify potential impact paths based on changed files

### 6.3 Simulation Manifest (`manifest.py`)
- Generate YAML manifests for Chaos Mesh experiments
- Configure network latency parameters
- Define target services based on the causal graph

### 6.4 E2B Runtime (`e2b_runtime.py`)
- Implement low-level E2B wrapper functions
- Handle container lifecycle management
- Execute commands in the sandbox environment

### 6.5 Sandbox Management (`sandbox.py`)
- Implement high-level sandbox management functions
- Set up k3d clusters inside the sandbox
- Deploy Chaos Mesh for fault injection
- Clean up resources after simulation

### 6.6 Fault Injection (`fault_driver.py`)
- Apply network latency faults using Chaos Mesh
- Monitor the system during fault injection
- Collect metrics and logs

### 6.7 LangGraph Workflow (`langgraph_flow.py`)
- Implement `run_sim(payload, repo_path)` as the main entry point
- Define the workflow steps and state passing
- Orchestrate the entire simulation process

### 6.8 Explanation Generation (`explanation.py`)
- Process collected metrics
- Calculate risk scores based on service impact
- Generate human-readable explanations

### 6.9 Attestation (`write_attest.py`)
- Create attestation JSON with the following keys:
  - `sim_id`
  - `manifest_hash`
  - `commit_target`
  - `metrics`
  - `timestamp`
  - `diff_hash`
- Store attestation at `.arc/.attest/{sim_id}.json`

### 6.10 Mocks (`mocks.py`)
- Implement `MockE2BHandle` for testing E2B integration
- Implement `MockFaultDriver` for testing fault injection
- Provide test fixtures for unit and integration tests

## 7. Risk Mitigation

1. **Performance** - Ensure the simulation runs efficiently (≤15 min)
2. **Resource Usage** - Properly clean up sandbox environments
3. **Error Handling** - Implement robust error handling for all external dependencies
4. **Security** - Ensure sandbox isolation for safe simulation
5. **Compatibility** - Test across different operating systems and Python versions

## 8. 16-Day Implementation Timeline

### Week 1: Foundation
- **Day 1**: Set up command structure and project scaffolding
- **Day 2**: Implement diff analysis using GitPython
- **Day 3**: Implement causal graph derivation
- **Day 4**: Create simulation manifest generator
- **Day 5**: Set up E2B runtime wrapper

### Week 2: Core Functionality
- **Day 6**: Implement sandbox management
- **Day 7**: Implement fault injection with Chaos Mesh
- **Day 8**: Create LangGraph workflow orchestration
- **Day 9**: Implement metrics collection and analysis
- **Day 10**: Implement explanation generation

### Week 3: Finalization
- **Day 11**: Implement attestation generation
- **Day 12**: Create unit tests for all modules
- **Day 13**: Create integration tests for the full workflow
- **Day 14**: Add documentation and examples
- **Day 15**: Perform end-to-end testing and bug fixes
- **Day 16**: Final review and submission

## 9. Future Enhancements

1. Additional fault scenarios beyond network_latency
2. More sophisticated causal graph derivation
3. Integration with CI/CD pipelines
4. Enhanced visualization of simulation results
5. Support for multi-service simulations

## 10. Dependency Updates

The following dependencies need to be added to `pyproject.toml`:

```toml
[project.dependencies]
langgraph = "^0.0.15"
kubernetes_asyncio = "^32.3.2"
e2b = "^0.12.0"
gitpython = "^3.1.40"
pyyaml = "^6.0.1"
```

## 11. Integration with Existing Arc Memory Architecture

To ensure seamless integration with the existing Arc Memory codebase, we need to consider the following aspects:

### 11.1 Configuration Management

We will leverage the existing configuration system in `arc_memory/config.py` by adding a new section for simulation settings:

```python
# Add to DEFAULT_CONFIG in config.py
"sim": {
    "default_scenario": "network_latency",
    "default_severity": 50,
    "default_timeout": 600,
}
```

This will allow users to customize default settings for the simulation command.

### 11.2 Telemetry Integration

We will integrate with the existing telemetry system in `arc_memory/telemetry.py` to track command usage:

```python
track_cli_command("sim", args={
    "range": range_value,
    "scenario": scenario,
    "severity": severity,
    "timeout": timeout,
    # Don't include sensitive data
})
```

### 11.3 Attestation Storage

We will store attestation files at `.arc/.attest/{sim_id}.json`, ensuring this directory is created using the existing `ensure_arc_dir()` function from `arc_memory/sql/db.py` with a subdirectory for attestations.

### 11.4 Dependency Management

In addition to updating `pyproject.toml`, we will also update `arc_memory/dependencies.py` to include simulation dependencies:

```python
# Add to OPTIONAL_DEPENDENCIES in dependencies.py
"sim": ["langgraph", "e2b", "pyyaml"],
```

### 11.5 Environment Variables and API Keys

We will need to manage environment variables for E2B, LangGraph, and LLM API access. We'll implement this by:

1. Creating a `.env.example` file in the repository root with placeholders:

```
# E2B API Key
E2B_API_KEY=your_e2b_api_key_here

# LLM API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LangGraph Configuration
LANGGRAPH_API_KEY=your_langgraph_api_key_here
```

2. Adding environment variable handling in the configuration system:

```python
# Add to config.py
def load_env_vars():
    """Load environment variables from .env file if available."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value
```

3. Adding a section in the configuration for API keys:

```python
# Add to DEFAULT_CONFIG in config.py
"api_keys": {
    "e2b": None,  # Will be loaded from E2B_API_KEY env var
    "openai": None,  # Will be loaded from OPENAI_API_KEY env var
    "anthropic": None,  # Will be loaded from ANTHROPIC_API_KEY env var
},
```

4. Updating the documentation to explain the environment variable requirements:

```markdown
# Environment Setup

The `arc sim` command requires several API keys to function:

- **E2B API Key**: Required for sandbox environments
- **LLM API Key**: Required for explanation generation (OpenAI or Anthropic)

You can set these up by:

1. Creating a `.env` file in your repository root
2. Adding your API keys in the format shown in `.env.example`
3. Or setting them as environment variables in your shell
```

### 11.6 Error Handling

We will create specific error classes in `arc_memory/errors.py` for simulation-related errors:

```python
class SimulationError(ArcMemoryError):
    """Base class for simulation errors."""
    pass

class SandboxError(SimulationError):
    """Error in sandbox environment."""
    pass

class FaultInjectionError(SimulationError):
    """Error in fault injection."""
    pass
```

### 11.7 Logging

We will use the existing logging configuration from `arc_memory/logging_conf.py`:

```python
from arc_memory.logging_conf import configure_logging, get_logger, is_debug_mode

logger = get_logger(__name__)
```

### 11.8 Reusing Existing Code

We will leverage existing code where appropriate:

1. The existing graph database access in `sql/db.py` for causal graph derivation
2. The existing model classes in `schema/models.py` for representing entities
3. Patterns from `cli/trace.py` for diff analysis

### 11.9 Documentation Updates

In addition to adding `docs/cli/sim.md` and updating `README.md`, we will also update:

1. `CHANGELOG.md` to include the new feature
2. `docs/examples/simulation.md` with usage examples

## 12. Conclusion

This implementation plan provides a structured approach to developing the `arc sim` command for Arc Memory. By following this plan and ensuring proper integration with the existing architecture, we will create a powerful tool that helps developers understand the potential impact of their code changes before they are merged, significantly enhancing the value proposition of Arc Memory.
