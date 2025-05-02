# Final Implementation Plan for Arc Memory VS Code Extension

This document outlines the detailed implementation plan for completing the final tasks required for the Arc Memory VS Code Extension Beta 0.1 release. The plan is based on a thorough analysis of the current codebase, the Arc Memory SDK documentation, and the requirements specified in the final tasks document.

## Project Context

We have two public packages:
1. **arc-memory (SDK)** – Python CLI (`arc build`, `arc trace`) that builds/queries a local SQLite temporal knowledge graph (TKG).
2. **arc-extension** – VS Code extension (TypeScript) that currently:
   - Shows hover provenance in `diff` views via `HoverProvider`
   - Spawns `arc trace file …` through `RpcClient`
   - Contains stub commands for "Ask Arc" and "Add Decision"

The graph currently only refreshes when a user runs `arc build` manually. Ollama is installed locally and will be used for the Ask Arc feature.

**Goal of this sprint**: Deliver an MVP "query-review-capture" loop for beta testers with minimal friction.

## Implementation Plan by Task

### 1. Test Current VS Code Interface

#### Integration Test Implementation
- Create a new test file: `src/test/integration/hoverProvider.integration.test.ts`
- Implement a test that:
  - Opens a diff view with sample content
  - Verifies gutter dots are applied to added/removed lines
  - Simulates hovering over a dot
  - Verifies an RPC call is made to `arc trace file`
  - Verifies the hover card renders with the correct markdown content

#### GitHub Action Workflow
- Create `.github/workflows/ci-extension.yml` with:
  - Node.js setup
  - VS Code Extension Test CLI setup
  - Dependency installation
  - Test execution
  - Reporting of test results

#### Testing Approach Considerations
- Use VS Code's Extension Testing API
- Mock the RPC client to avoid actual SDK calls during tests
- Create test fixtures with sample diff content and trace responses
- Handle the known limitations with stubbing Node.js built-in modules

### 2. Add "Arc: Refresh Graph" Command

#### Directory Structure
- Create `src/commands/RefreshGraph.ts`
- Create `src/events/EventEmitter.ts` for the event system

#### Command Registration
- Update `package.json` to register `arc-memory.refreshGraph` with keybindings:
  - macOS: `⇧⌘R` (Shift+Command+R)
  - Windows/Linux: `Ctrl+Shift+R`
  - Add `"when": "editorTextFocus && !renameInputVisible"` condition to avoid conflicts with VS Code's "Rename Symbol"

#### Command Implementation
- Implement `RefreshGraph.ts` to:
  - Get or create an integrated terminal named "Arc Build"
  - Execute `arc build --incremental --quiet`
  - Show status bar message during execution
  - Parse terminal output to detect completion
  - Publish `arcMemory.graphRefreshed` event on success
  - Ensure proper shell quoting for Windows compatibility

#### Post-Commit Reminder
- Add a file system watcher for `.git/COMMIT_EDITMSG`
- When detected, show a toast notification
- Include the keyboard shortcut in the notification

#### Cache Invalidation
- Subscribe to `arcMemory.graphRefreshed` event in HoverProvider
- Clear the PrefetchQueue cache when the event is fired
- Call `updateDecorations()` on all visible editors to refresh gutter dots

#### SDK Integration Details
- Use `arc build --incremental --quiet` for fast updates
- Handle exit codes as specified in the SDK contract:
  - Code 0: Success
  - Code 10: Arc not initialized (graph.db missing)
  - Code 20: Auth error
  - Other non-zero: SDK failure

### 3. Wire Ask Arc to Local Ollama Model

#### Directory Structure
- Create `src/ollama/OllamaClient.ts`
- Create `src/ollama/types.ts`
- Create `src/views/AskArcWebview.ts`

#### Ollama Client Implementation
- Implement `OllamaClient.ts` to:
  - Connect to `http://127.0.0.1:11434/api/generate`
  - Support streaming responses
  - Handle errors and timeouts
  - Use the "gemma3:4b-it-qat" model
  - Add availability check using `/api/tags` endpoint
  - Implement graceful degradation when Ollama is not running

#### Command Enhancement
- Update the existing Ask Arc command to:
  - Check for text selection first
  - If selection exists, get file path and line number
  - Use RPC client to get trace data for that location
  - If no selection, prompt user to select code or hover a diff
  - Format the context and question for the Ollama model
  - Use the specified system prompt
  - Add feature flag `arc.memory.experimental.askArc` (default: true)

#### Webview Implementation
- Create a webview to display Ask Arc responses
- Implement markdown rendering
- Add a copy-to-clipboard button
- Show streaming responses in real-time
- Include citation formatting
- Add error handling for Ollama connection issues

#### Performance Monitoring
- Add latency tracking for Ollama requests
- Log first token time and total response time
- Ensure < 1s latency to first token as per success criteria
- Add telemetry opt-in prompt on first use

### 4. Autogenerate ADR / `.rules` File from Fixes

#### Directory Structure
- Create `src/providers/CodeActionProvider.ts`

#### Change Detection
- Enhance `HoverProvider.ts` to:
  - Track lines that have gutter dots
  - Listen for `textDocument/onDidChange` events
  - Detect when changes are made to lines that had dots

#### CodeAction Provider
- Implement `CodeActionProvider.ts` to:
  - Register for relevant file types
  - Detect changes to previously marked lines
  - Offer a quick-fix action of kind `quickfix.arc.captureRule`
  - Add feature flag `arc.memory.experimental.ruleCapture` (default: true)

#### Rule Capture Implementation
- When the quick-fix is invoked:
  - Use the existing AddDecision command helper to open an ADR template
  - Create `.arc/rules.yml` if it doesn't exist
  - Append a new rule with glob pattern, rule text, and commit SHA
  - Emit `arcMemory.ruleCaptured` telemetry event
  - Use timestamp in ADR filename to prevent collisions: `ADR_<timestamp>.md`
  - Include file path in the Context section for uniqueness

#### Performance Optimization
- Ensure quick-fix appears within 3s of file save as per success criteria
- Optimize change detection to minimize performance impact
- Cache previously detected lines to improve performance

## Common Infrastructure

### Event System
- Implement a simple event emitter in `src/events/EventEmitter.ts`
- Support events:
  - `arcMemory.graphRefreshed`
  - `arcMemory.ruleCaptured`
- Allow components to subscribe to and publish events
- Ensure proper cleanup of event listeners on deactivation

### Error Handling
- Implement consistent error handling across all components
- Log errors to the output channel
- Show user-friendly error messages
- Handle SDK-specific error codes appropriately
- Add first-run SDK check using `arc doctor --quiet`
- Offer to run initial build if graph is missing

### Telemetry
- Implement basic telemetry for tracking:
  - Command usage
  - Performance metrics
  - Error rates
  - Rule capture events
- Add telemetry opt-in prompt on first activation
- Store consent in `globalState`
- Provide option to disable telemetry later

### Feature Flags
- Implement feature flags for experimental features:
  - `arc.memory.experimental.askArc` (default: true)
  - `arc.memory.experimental.ruleCapture` (default: true)
- Add settings descriptions in package.json
- Check flags before executing related functionality

## Implementation Sequence and Branches

### Branch: `feat/integration-tests`
1. Set up integration test infrastructure
2. Implement hover provider integration test
3. Create GitHub Action workflow with Windows & macOS matrix
4. Add caching for Ollama models in CI
5. Add lint step in CI
6. Verify tests pass locally

### Branch: `feat/refresh-graph`
1. Implement event system
2. Create RefreshGraph command
3. Add post-commit reminder
4. Update package.json with keybindings and when clause
5. Implement cache invalidation for graph refreshes
6. Add first-run SDK check
7. Test the command functionality

### Branch: `feat/ask-arc-ollama`
1. Implement OllamaClient with availability check
2. Enhance Ask Arc command
3. Create AskArc webview
4. Implement feature flag
5. Add telemetry opt-in
6. Test with local Ollama instance
7. Test degraded mode when Ollama is not running
8. Measure and optimize latency

### Branch: `feat/capture-rule`
1. Enhance HoverProvider for change detection
2. Implement CodeActionProvider
3. Add rule capture functionality
4. Implement feature flag
5. Add timestamp to ADR filenames
6. Test quick-fix appearance and timing
7. Verify ADR template generation
8. Test the full feedback loop

## Success Criteria Verification

### Refresh Graph
- Measure build time on repositories of various sizes
- Verify p95 build time < 3s on repos ≤ 5000 commits
- Confirm status bar is cleared on success
- Verify hover shows new commit without window reload after refresh
- Test the full workflow: open diff → commit → toast appears → ⇧⌘R → hover shows new commit

### Ask Arc
- Measure latency to first token
- Verify < 1s latency to first token
- Confirm answers include ≥ 1 provenance citation when available
- Test degraded mode when Ollama is not running
- Verify error handling shows user-friendly messages

### Rule Capture
- Measure time from file save to quick-fix appearance
- Verify quick-fix appears within 3s
- Confirm ADR doc auto-opens correctly
- Test the full feedback loop: light-bulb → rule saved → next hover on similar change shows rule badge

### Tests
- Verify CI passes in GitHub Actions on PRs
- Confirm hover test correctly asserts provenance markdown
- Ensure tests pass on both Windows and macOS
- Verify lint checks pass on new files

## Important Constraints

- Do **not** modify SDK internals; call the CLI only
- Keep all new extension code under `src/` and update `esbuild.js` bundle list to include new directories
- Hard-code Ollama model in dev preview; prepare for future configuration
- Maintain existing lint rules & `strict` TypeScript compiler flags
- Ensure Windows compatibility for all commands and keybindings
- Follow VS Code extension best practices for UI/UX and performance

## Checkpoints & Deliverables

1. **After Task 1**:
   - Push branch `feat/integration-tests`
   - Verify CI workflow runs successfully on both Windows and macOS
   - Share test coverage report

2. **After Task 2**:
   - Push branch `feat/refresh-graph`
   - Run tests to verify functionality
   - Create and share demo GIF showing the refresh workflow
   - Demonstrate the cache invalidation working (hover shows new commit without reload)

3. **After Task 3**:
   - Open PR `feat/ask-arc-ollama`
   - Attach latency logs showing performance metrics
   - Include documentation on Ollama setup requirements
   - Demonstrate graceful degradation when Ollama is not running

4. **After Task 4**:
   - Open PR `feat/capture-rule`
   - Include screenshot of light-bulb quick-fix
   - Demonstrate the full workflow from code change to ADR generation
   - Show the feedback loop working (rule badge appears on similar changes)

5. **Final Deliverables**:
   - Update README.md with new features and usage instructions
   - Create CHANGELOG.md for marketplace readiness
   - Update package.json to version `0.0.1-beta.0`
   - Create release tag

## SDK Integration Reference

### Key CLI Commands

1. **Trace Command**:
   ```bash
   arc trace file FILE_PATH LINE_NUMBER --format=json --max-results=3 --max-hops=2
   ```
   - Used by: HoverProvider, Ask Arc command
   - Returns: JSON array of events in the decision trail
   - Performance: Should complete in < 200ms

2. **Build Command**:
   ```bash
   arc build --incremental --quiet
   ```
   - Used by: RefreshGraph command
   - Performance: Should complete in < 3s for repos ≤ 5000 commits
   - Exit codes: 0 (success), 10 (not initialized), 20 (auth error)

### Data Formats

1. **Trace Response Format**:
   ```json
   {
     "events": [
       {
         "type": "commit",
         "title": "Fix bug in login form",
         "id": "abc123",
         "source": "https://github.com/example/repo/commit/abc123",
         "timestamp": "2023-04-15T14:32:10Z",
         "metadata": { ... }
       },
       ...
     ]
   }
   ```

2. **Rules File Format** (YAML):
   ```yaml
   - pattern: "src/auth/**/*.ts"
     rule: "Token expiry must be set to 900 seconds"
     commit: "abc123"
     date: "2023-04-15T14:32:10Z"
   ```

## Refinements and Edge Cases

To avoid first-impression snags and gather clean telemetry, we need to address several edge cases and UX considerations. These refinements don't require architectural changes but will significantly improve the user experience for beta testers.

### Execution & Architecture Gaps

| Area | What's Missing | Why It Matters | Quick Fix |
|------|----------------|----------------|-----------|
| **Event consumption** | You define `arcMemory.graphRefreshed`, but no listener invalidates the provenance cache or re-decorates open editors. | Users may refresh graph yet still see stale hovers until file reload. | In `HoverProvider.updateDecorations`, subscribe to the event emitter and call `this.updateDecorations()` on all visible editors. |
| **First-run SDK check** | If testers install extension before running **any** `arc build`, commands throw exit-code 10. | Prevents the "it just works" impression. | On activation: run `arc doctor --quiet`. If graph missing, offer "Run initial build now (takes <30 s)". |
| **Ollama availability** | Plan doesn't handle "Ollama not running / model not pulled". | 1-line Ask Arc => scary stack trace. | Before first call, hit `/api/tags`. If 404/ECONNREFUSED, show modal: "Start Ollama or disable Ask Arc." |
| **Telemetry opt-in** | You log command usage & perf, but no consent UI. | Privacy expectation, esp. EU beta testers. | On first activation ask: "Share anonymised metrics to improve Arc?" → store in `globalState`. |
| **Windows shell quoting** | Terminal `sendText('arc build --incremental --quiet')` is fine on PowerShell, but keybinding (Ctrl-Shift-R) may collide with VS Code's default "Rename Symbol". | Shortcut silently fails for some users. | Include `"when": "editorTextFocus && !renameInputVisible"` or choose non-conflicting key (`Ctrl-Alt-R`). |
| **CI cache for Ollama tests** | Ask Arc tests will timeout in GitHub Actions unless model layer is cached. | Flaky pipeline. | In `ci-extension.yml` add a cache step for `~/.ollama/models` or skip Ask Arc tests on CI (mock Ollama). |
| **ADR slug collisions** | Multiple quick-fixes in same session may open identical untitled docs. | Losing edits. | Name doc `ADR_<timestamp>.md`; prefill the "Context" header with current file path for uniqueness. |

### Polish & Documentation

| Topic | Added Detail |
|-------|--------------|
| **README updates** | Document ⇧⌘R flow, Ollama install, and "Ask Arc" demo GIF. |
| **Extension changelog** | Create `CHANGELOG.md` for marketplace readiness (VS Code requires it). |
| **Version bump / semver** | Update `package.json` to `0.0.1-beta.0`; script `npm run release` to tag. |
| **ESBuild include list** | Ensure new `src/ollama/**` and `src/events/**` are in the bundle glob. |
| **Lint & Prettier** | Add lint step in CI so PRs fail fast on style errors introduced by new files. |
| **Feature flags** | Wrap Ask Arc and rule capture behind `arc.memory.experimental` setting so you can disable quickly if beta feedback spikes. |

### Acceptance Checklist Add-ons

1. **Graph refresh UX**
   *Open diff → commit → toast appears → ⇧⌘R → hover shows new commit *without* window reload.*
2. **Ask Arc degraded mode**
   When Ollama down, command shows modal *and* returns gracefully (no stack trace in logs).
3. **Rule capture loop**
   Light-bulb → rule saved → next hover on similar change shows rule badge (prove feedback loop works).
4. **CI green on Windows & macOS matrix**
   Ensures PowerShell quoting and keybindings don't regress.

## Additional Implementation Considerations

### Code Style and Best Practices

As this repository will be open source and used by early beta customers, we will adhere to the following principles:

1. **VS Code Extension Best Practices**:
   - Clear separation of concerns (providers, commands, views)
   - Proper error handling and logging
   - Efficient resource usage
   - Following VS Code's extension guidelines for UI/UX

2. **Lightweight Implementation**:
   - Keep the implementation focused on delivering the core functionality outlined in the product strategy
   - Avoid over-engineering or adding unnecessary features
   - Design for future iterations based on customer feedback

3. **Alignment with Product Strategy**:
   - Fast context retrieval (< 500ms)
   - Verifiable provenance with citations
   - Minimal UI that stays out of the way until needed
   - Privacy-first approach with local processing

4. **Code Quality**:
   - Well-structured and maintainable code
   - Comprehensive documentation
   - Consistent error handling
   - Thorough testing

### Ollama Integration Details

Based on the [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md), we will implement the following:

1. **Generate API Endpoint**:
   ```
   POST http://127.0.0.1:11434/api/generate
   ```

2. **Request Format**:
   ```json
   {
     "model": "gemma3:4b-it-qat",
     "prompt": "System prompt + user question + context",
     "stream": true
   }
   ```

3. **Streaming Response Handling**:
   - Process the streaming JSON responses line by line
   - Update the webview in real-time as tokens are received
   - Track the time to first token for performance monitoring

4. **Error Handling**:
   - Handle cases where Ollama is not running
   - Handle model not found errors
   - Implement proper timeout handling
   - Provide user-friendly error messages

### SDK Performance Considerations

The Arc Memory SDK has been benchmarked (https://github.com/Arc-Computer/arc-memory/tree/main/benchmarks) and our focus will be on:

1. **Proper CLI Command Invocation**:
   - Correctly invoke the Arc Memory SDK CLI commands
   - Use the recommended flags for optimal performance

2. **Efficient Rendering**:
   - Minimize processing overhead in the extension
   - Optimize the rendering of hover cards and webviews
   - Implement caching where appropriate

3. **User Experience**:
   - Focus on the user experience rather than re-benchmarking the SDK
   - Ensure the UI remains responsive during SDK operations
   - Provide appropriate feedback during longer operations

## Conclusion

This implementation plan provides a detailed roadmap for completing the final tasks required for the Arc Memory VS Code Extension Beta 0.1 release. By following this plan and adhering to the additional considerations outlined above, we will deliver an MVP "query-review-capture" loop for beta testers with minimal friction, meeting all the specified success criteria while maintaining high code quality standards appropriate for an open-source project.
