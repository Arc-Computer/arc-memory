# ADR Formatting Guide

This guide explains how to format Architecture Decision Records (ADRs) for use with Arc Memory.

## ADR Structure

Arc Memory expects ADRs to be Markdown files with YAML frontmatter. The basic structure is:

```markdown
---
title: Title of the ADR
date: 2023-11-15
status: accepted
decision_makers: ["Person A", "Person B"]
---

# Title

## Context

Describe the context and problem statement...

## Decision

The decision that was made...

## Consequences

What becomes easier or more difficult because of this change...
```

## Required Frontmatter Fields

The following fields are required in the frontmatter:

- `title`: The title of the ADR
- `date`: The date when the decision was made
- `status`: The status of the decision (e.g., "proposed", "accepted", "rejected", "deprecated", "superseded")

## Date Formatting

The `date` field in the frontmatter can be in any of the following formats:

- ISO format: `2023-11-15`
- ISO format with time: `2023-11-15T14:30:00`
- ISO format with microseconds: `2023-11-15T14:30:00.123456`
- Slash format: `2023/11/15`
- European format: `15-11-2023`
- European slash format: `15/11/2023`
- Month name format: `November 15, 2023`
- Abbreviated month format: `Nov 15, 2023`

For consistency, we recommend using the ISO format (`YYYY-MM-DD`).

## Status Values

The `status` field should be one of the following values:

- `proposed`: The decision is still being discussed
- `accepted`: The decision has been accepted and is being implemented
- `rejected`: The decision has been rejected
- `deprecated`: The decision was accepted but is no longer relevant
- `superseded`: The decision has been replaced by a newer decision

## Decision Makers

The `decision_makers` field can be either a string (for a single decision maker) or an array of strings (for multiple decision makers).

```yaml
# Single decision maker
decision_makers: "Person A"

# Multiple decision makers
decision_makers: ["Person A", "Person B", "Person C"]
```

## Example ADR

Here's a complete example of a well-formatted ADR:

```markdown
---
title: Use SQLite for Knowledge Graph Storage
date: 2023-11-15
status: accepted
decision_makers: ["Jarrod Barnes", "Engineering Team"]
---

# Use SQLite for Knowledge Graph Storage

## Context

We need a storage solution for the knowledge graph that is:
- Simple to set up and use
- Doesn't require a separate server
- Supports SQL queries
- Can be embedded in the application

## Decision

We will use SQLite as the storage backend for the knowledge graph.

## Consequences

### Positive

- No separate database server to set up
- Simple to use and understand
- Good performance for read-heavy workloads
- Easy to distribute as part of the application

### Negative

- Limited concurrency for write operations
- Not suitable for distributed deployments
- May need to migrate to a more robust solution if scale increases significantly
```

## Troubleshooting

### Date Parsing Issues

If you see warnings like "Could not parse date" in the logs, make sure your date is in one of the supported formats. The most reliable format is ISO format (`YYYY-MM-DD`).

### Missing Required Fields

If required fields are missing, Arc Memory will use default values:
- Missing `title`: Uses the filename
- Missing `date`: Uses the current date and time
- Missing `status`: Uses "unknown"

For best results, always include all required fields.
