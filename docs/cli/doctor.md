# Doctor Commands

The Arc Memory CLI provides diagnostic commands to check the health of your knowledge graph and provide information about its contents.

**Related Documentation:**
- [Authentication Commands](./auth.md) - Authenticate with GitHub
- [Build Commands](./build.md) - Build your knowledge graph
- [Trace Commands](./trace.md) - Trace history in your graph
- [Building Graphs Examples](../examples/building-graphs.md) - Examples of building graphs

## Overview

The doctor command checks the status of the Arc Memory database, verifies its integrity, and provides statistics about the knowledge graph. It's useful for troubleshooting and understanding what's in your graph.

## Commands

### `arc doctor`

Check the status of the Arc Memory database and provide statistics.

```bash
arc doctor [OPTIONS]
```

This command checks if the database files exist, decompresses the database if needed, and provides statistics about the nodes and edges in the knowledge graph.

#### Options

- `--debug`: Enable debug logging.

#### Example

```bash
# Check the status of the Arc Memory database
arc doctor

# With debug logging
arc doctor --debug
```

## Output

The doctor command outputs several tables with information about the knowledge graph:

### Files Table

Shows the status and size of important files:

```
┌───────────────────┬────────┬─────────┐
│ File              │ Status │ Size    │
├───────────────────┼────────┼─────────┤
│ ~/.arc/graph.db   │ Exists │ 2.5 MB  │
│ ~/.arc/graph.db.zst│ Exists │ 0.8 MB  │
│ ~/.arc/manifest.json│ Exists │ 1.2 KB  │
└───────────────────┴────────┴─────────┘
```

### Database Table

Shows statistics about the database:

```
┌────────┬───────┐
│ Metric │ Value │
├────────┼───────┤
│ Nodes  │ 1250  │
│ Edges  │ 3750  │
└────────┴───────┘
```

### Build Manifest Table

Shows information from the build manifest:

```
┌─────────────────┬─────────────────────────┐
│ Metric          │ Value                   │
├─────────────────┼─────────────────────────┤
│ Build Time      │ 2023-04-23T15:42:10     │
│ Schema Version  │ 1.0                     │
│ Node Count      │ 1250                    │
│ Edge Count      │ 3750                    │
│ Last Commit Hash│ abc123def456            │
└─────────────────┴─────────────────────────┘
```

## Automatic Fixes

The doctor command performs some automatic fixes:

1. **Database Decompression**: If the compressed database exists but the uncompressed one doesn't, it will automatically decompress it.

## Overall Status

At the end, the doctor command provides an overall status:

- **Ready to Use**: If the database exists and is valid.
- **Not Set Up**: If the database doesn't exist, with instructions to run `arc build`.

## When to Use

Use the doctor command in the following situations:

1. **After Installation**: To verify that Arc Memory is set up correctly.
2. **After Building**: To check that the build process completed successfully.
3. **Troubleshooting**: When you encounter issues with other commands.
4. **Performance Concerns**: To check the size of your knowledge graph.

## Troubleshooting

If the doctor command reports issues:

1. **Missing Files**: Run `arc build` to create the knowledge graph.
2. **Database Errors**: If there are errors querying the database, try rebuilding it with `arc build`.
3. **Manifest Errors**: If the manifest is invalid, run a full build with `arc build` (without `--incremental`).
4. **Debug Mode**: Run with `--debug` flag to see detailed logs: `arc doctor --debug`
