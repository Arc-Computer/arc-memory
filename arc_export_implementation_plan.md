# Arc Export Command Implementation Plan

## Overview

This document outlines the implementation plan for the new `arc export` command in the Arc Memory CLI. This command will export a relevant slice of the knowledge graph as a JSON file for use in GitHub App PR review workflows.

## Requirements

The `arc export` command will:

1. Export a relevant slice of the knowledge graph as a JSON file
2. Focus on files modified in a PR and their related nodes/edges
3. Support compression and optional GPG signing
4. Be used in GitHub Actions to provide context for PR reviews

## Command Signature

```
arc export --pr <PR_SHA> --out <OUTPUT_FILE> [--compress] [--sign] [--key <GPG_KEY_ID>]
```

### Parameters

- `--pr`: SHA of the PR head commit (required)
- `--out`: Output file path for the JSON (required)
- `--compress`: Boolean flag to enable compression (optional, default: True)
- `--sign`: Boolean flag to enable GPG signing (optional, default: False)
- `--key`: GPG key ID to use for signing (optional)

## Export Format (arc-graph.json)

The exported JSON will follow this structure:

```json
{
  "schema_version": "0.2",
  "generated_at": "2023-05-08T14:23Z",
  "pr": {
    "number": 123,
    "title": "Add payment processing",
    "author": "alice",
    "changed_files": ["src/payments/api.py", "src/payments/models.py"]
  },
  "nodes": [
    {
      "id": 42,
      "type": "FILE",
      "path": "src/payments/api.py",
      "metadata": { /* file-specific metadata */ }
    },
    {
      "id": 77,
      "type": "ADR",
      "title": "Payment Gateway Selection",
      "path": "docs/adrs/001-payment-gateway.md",
      "metadata": { /* ADR-specific metadata */ }
    }
    // Additional nodes...
  ],
  "edges": [
    {
      "src": 42,
      "dst": 77,
      "type": "LINKS_ADR",
      "metadata": { /* edge-specific metadata */ }
    }
    // Additional edges...
  ],
  "sign": {
    "gpg_fpr": "ABCD1234...",
    "sig_path": "arc-graph.json.gz.sig"
  }
}
```

## Graph Scoping Algorithm

The command will intelligently determine which parts of the graph to export:

1. Start with files modified in the PR (comparing PR head with base branch)
2. Include direct relationships (1-hop neighbors)
3. Always include linked ADRs regardless of hop distance
4. Include Linear tickets referenced in the PR or commits
5. Include recent changes to the modified files (last 3-5 commits)
6. Apply filtering to keep the export size manageable (target: ≤250KB)

## Implementation Plan

### 1. Create a New Command Module

Create a new file `arc_memory/cli/export.py` for the export command, following the pattern of other CLI commands.

### 2. Add the Command to the CLI

Update `arc_memory/cli/__init__.py` to import and register the new export command.

### 3. Implement the Export Logic

Create a new module `arc_memory/export.py` to implement the core export functionality:

- Query the database for files modified in a PR
- Expand to include related nodes (1-hop neighbors)
- Include ADRs and Linear tickets
- Format the data according to the specified JSON schema
- Apply filtering to keep the export size manageable

### 4. Add Compression and Signing Support

Leverage the existing compression functionality in `arc_memory/sql/db.py` and add GPG signing support.

### 5. Add Tests

Create unit and integration tests for the new functionality.

### 6. Update Documentation

Update the documentation to include information about the new command.

## Key Files to Modify

1. `arc_memory/cli/__init__.py` - Add the new command
2. `arc_memory/cli/export.py` - Implement the command interface
3. `arc_memory/export.py` - Implement the core export functionality
4. `tests/unit/test_export.py` - Add unit tests
5. `tests/integration/test_export.py` - Add integration tests
6. `docs/api/export.md` - Add documentation

## Success Criteria

- Command successfully exports a relevant slice of the graph
- Export includes all necessary context for PR review
- Export size remains manageable (≤250KB for typical PRs)
- Process is efficient and doesn't significantly slow down CI
- JSON format is compatible with the GitHub App's needs
