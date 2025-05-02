**Plan: VS Code Extension Demo - Core Hover & Setup Guidance**

**1. Goal:**
Create a functional VS Code extension demo that:
*   Displays a hover card with decision trail information (fetched via `arc trace file --format=json`) when hovering over changed lines in a diff view.
*   Includes a placeholder "Ask Arc" command link on the hover card.
*   On activation, checks for basic prerequisites and guides the user/presenter with manual setup steps if needed, providing context on the underlying SDK requirements.

**2. Assumptions:**
*   Node.js and Git are installed.
*   The demo presenter will have manually:
    *   Installed `arc-memory==0.1.2` (or later) via `pip` or `uv`.
    *   Authenticated using `arc auth gh`.
    *   Successfully run `arc build` in the target Git repository workspace.
    *   Optionally installed Ollama and pulled a model (`phi3:mini`) if intending to show the "Ask Arc" context logging.
*   The `arc` command is available in the system's PATH where VS Code is launched.

**3. Implementation Steps:**

*   **Step 1: Project Initialization & Scaffolding**
    *   **Action:** Use the official Yeoman generator: `npx --package yo --package generator-code -- yo code`.
    *   **Action:** Select "New Extension (TypeScript)". Provide name (`arc-memory-vscode`), identifier (`arc-memory`), description. Initialize git repo, choose bundler (esbuild/webpack recommended for smaller bundle, or unbundled for simplicity initially), use npm/yarn.
    *   **Action:** Open the generated folder in VS Code.
    *   **Action:** Install essential development dependencies if not already added: `@types/vscode`, `@types/node`.
    *   **Action:** Create the directory structure based on `filestructure.md` (`src/rpc/`, `src/providers/`, `src/util/`, `test/`, etc.) and create placeholder `.ts` files within them (`RpcClient.ts`, `types.ts`, `HoverProvider.ts`).

*   **Step 2: Setup Check & Guidance (On Activation)**
    *   **Focus:** `src/extension.ts` (the `activate` function).
    *   **Action:** Implement a simple async function `checkPrerequisites()`:
        *   Check 1: Attempt to run `arc --version` using `child_process.exec`. If it fails or throws an error, assume `arc` is not installed or not in PATH.
        *   Check 2: Check if the default graph DB exists (e.g., `fs.existsSync(path.join(os.homedir(), '.arc', 'graph.db'))`). This is a basic heuristic for `arc build` having run.
    *   **Action:** In `activate`, call `await checkPrerequisites()`.
    *   **Action:** If checks fail:
        *   Show an error notification: `vscode.window.showErrorMessage('Arc Memory prerequisites not met.', 'Show Setup Guide', 'Check Again', 'Dismiss')`.
        *   Handle button clicks:
            *   `Show Setup Guide`: Opens the `SETUP_GUIDE.md` file (see Step 8) in a VS Code editor tab (`vscode.workspace.openTextDocument` then `vscode.window.showTextDocument`).
            *   `Check Again`: Re-run `checkPrerequisites()` and potentially dismiss the current error message if checks now pass.
        *   Do *not* proceed with registering providers/commands until checks pass (or maybe allow providers but have them fail gracefully if `arc` isn't callable). For the demo, stopping activation is simpler.
    *   **Action:** If checks pass, log a confirmation to the debug console and proceed with provider/command registration.
    *   **Demo Narrative Emphasis (Transparency):** When demonstrating this step (or if the error message appears), verbally state: *"Before Arc activates, it checks if the core SDK and graph are ready. If not, it guides you through the setup [Show the SETUP_GUIDE.md briefly] – we believe being transparent about requirements is important for trust."*

*   **Step 3: RPC Client (Child Process Implementation)**
    *   **Focus:** `src/rpc/RpcClient.ts`, `src/rpc/types.ts`.
    *   **Action:** Define `TraceRequest` (`filePath: string`, `lineNumber: number`) and `TraceResponse` (array of event objects matching SDK JSON output) interfaces in `types.ts`.
    *   **Action:** Implement the `RpcClient` class (consider Singleton pattern).
    *   **Action:** Implement `async getTrace(request: TraceRequest): Promise<TraceResponse | null>`.
        *   Use `child_process.spawn` to execute `arc trace file "${request.filePath}" ${request.lineNumber} --format=json --max-results=3 --max-hops=2`.
        *   Handle `stdout`, `stderr`, exit code. Parse valid JSON from `stdout` on success (exit code 0).
        *   Log errors via `vscode.window.createOutputChannel("Arc Memory")`. Return `null` on any failure.
        *   Return parsed `TraceResponse` array on success.

*   **Step 4: Hover Provider Implementation**
    *   **Focus:** `src/providers/HoverProvider.ts`.
    *   **Action:** Implement `vscode.HoverProvider`.
    *   **Action (New - Inline Affordance):** Define a simple `vscode.TextEditorDecorationType` (e.g., using `gutterIconPath` with a Codicon like `$(circle-small-filled)` or `$(primitive-dot)`). Apply this decoration to all lines identified as changed (`+`/`-`) within the diff view upon activation or when the editor becomes visible.
    *   **Demo Narrative Emphasis (Unintrusive Presence):** When showing the diff view, point out the gutter dot: *"Arc signals unobtrusively with this small dot that it has context available for this line, staying out of the way until you need it."*
    *   **Action:** In `provideHover(document, position, token)`:
        *   Ensure `document.languageId === 'diff'`.
        *   Determine the corresponding file path and line number for the `position` within the actual workspace file (Requires parsing diff or using Git/SCM API - flag for refinement post-demo).
        *   Verify the line is a changed line.
        *   Get the `RpcClient` instance.
        *   `const traceResult = await rpcClient.getTrace({ filePath, lineNumber });`

*   **Step 5: Hover Card Rendering**
    *   **Focus:** `src/providers/HoverProvider.ts` (within `provideHover`).
    *   **Action:** If `traceResult` is valid (not null, potentially non-empty array):
        *   **Build Emphasis (Clarity & Minimalism):** Create `vscode.MarkdownString('', true)` (enable commands). Ensure the formatting closely follows the clean, minimal style of the mockups, limiting content to ~3 key events initially.
        *   **Build Emphasis (Provenance):** Format `traceResult` data into markdown explicitly showing event **type** (e.g., map to Codicons `$(git-commit)`, `$(git-pull-request)`, `$(book)`), **title/summary**, and **key identifier** (PR#, SHA prefix, ADR title).
        *   Add command links: `[Ask Arc](command:arc.askArc?${encodeURIComponent(JSON.stringify({filePath, lineNumber, traceData: traceResult}))})` and `[Open Timeline](command:arc.openTimeline?...)`.
        *   Return `new vscode.Hover(markdownString)`.
    *   **Action:** If `traceResult` is `null`, return `null`.
    *   **Demo Narrative Emphasis (Speed, Provenance, Clarity):** When the hover appears, emphasize: *"Notice how **quickly** Arc surfaces the context – the goal is under half a second. This isn't guessing; it's showing the **verifiable provenance**: the actual Pull Request [point], the Architecture Decision [point], etc. And it's presented **clearly and minimally**, giving just enough context to unblock you without noise."*

*   **Step 6: Placeholder Command Registration**
    *   **Focus:** `src/extension.ts` (the `activate` function, *after* prerequisite checks pass).
    *   **Action:** Register `arc.askArc`: `vscode.commands.registerCommand('arc.askArc', (context: {filePath: string, lineNumber: number, traceData: TraceResponse}) => { ... });`
    *   **Action:** Handler shows info message with context and logs trace data: `vscode.window.showInformationMessage(...); console.log('Ask Arc Context:', context);`
    *   **Demo Narrative Emphasis (Transparency):** When clicking "Ask Arc" and the placeholder appears: *"Clicking 'Ask Arc' uses this retrieved context [point to hover data] to feed a local LLM like Ollama for deeper questions. We've deferred the actual LLM call for this initial demo to focus on the core provenance retrieval, but the context is ready for it."*
    *   **Action:** Register `HoverProvider`: `context.subscriptions.push(vscode.languages.registerHoverProvider('diff', new HoverProvider(rpcClientInstance)));`

*   **Step 7: Package Configuration**
    *   **Focus:** `package.json`.
    *   **Action:** Verify `"main"` points to the compiled extension entry point (`./out/extension.js` or similar).
    *   **Action:** Set `"activationEvents": ["onLanguage:diff", "workspaceContains:**/.git", "onCommand:arc.askArc"]`.
    *   **Action:** Add command contribution for `arc.askArc` under `contributes.commands`.

*   **Step 8: Setup Guide Content**
    *   **Action:** Create a file `SETUP_GUIDE.md` in the extension's root.
    *   **Action:** Populate it with clear, step-by-step instructions for the manual setup:
        ```markdown
        # Arc Memory Extension - Manual Setup Guide

        This guide outlines the steps needed to prepare your environment for the Arc Memory VS Code extension demo. Please run these commands in your terminal.

        1.  **Install Arc Memory SDK (v0.1.2 or later):**
            ```bash
            pip install --upgrade arc-memory
            # or using uv
            # uv pip install --upgrade arc-memory
            ```

        2.  **Authenticate with GitHub:**
            ```bash
            arc auth gh
            ```
            *(Follow the browser prompts)*

        3.  **Build Knowledge Graph:**
            *Navigate to your Git repository folder in the terminal.*
            ```bash
            cd /path/to/your/repo
            arc build
            ```
            *(This may take a few minutes for larger repositories)*

        4.  **(Optional) Prepare Local LLM:**
            *Ensure Ollama is installed and running.*
            ```bash
            ollama pull phi3:mini
            ```

        5.  **Restart VS Code:** Ensure the extension picks up the changes.

        You can use the "Check Again" button in the VS Code notification to re-verify the setup after completing these steps.
        ```

*   **Step 9: Testing Strategy (Manual Demo Focus)**
    *   **Setup:** Perform the manual steps from `SETUP_GUIDE.md` in a test repository.
    *   **Run:** Launch the extension via VS Code Debugger (F5).
    *   **Verify Activation:** Ensure no setup error message appears (or test that it *does* appear if prerequisites are deliberately missing, and that the guide opens).
    *   **Verify Gutter Dot (New):** Confirm the gutter decoration appears on changed lines in the diff view.
    *   **Verify Hover:** Open diff view, hover over changed lines (`+`/`-`). Confirm hover appears, shows relevant data, looks like mockups, appears quickly.
    *   **Verify Command:** Click "Ask Arc" link. Confirm placeholder message appears with correct file/line context logged to Debug Console.
    *   **Verify Narrative Points (New):** Practice the verbal emphasis points related to speed, provenance, clarity, and transparency during test runs.
    *   **Check Errors:** Monitor Debug Console and "Arc Memory" Output Channel for errors.

**4. Demo Scope:**
*   **IN:** Project scaffolding, basic prerequisite checks + manual guide, **gutter dot indicator**, calling `arc trace file --format=json` via child process, rendering hover card from results (mimicking mockups), placeholder "Ask Arc" command.
*   **OUT (for initial demo):** Full automated onboarding, robust diff line-to-file mapping, actual Ollama integration for "Ask Arc", webview timeline, prefetching/caching, telemetry, Python RPC server (`arc rpc serve`), other commands (`Explain Diff`, `Build Graph`), Agent Mode integration, bundling optimizations.

---

This detailed plan provides a clear roadmap for building the VS Code extension demo, balancing speed with the need to provide context on the underlying setup.
