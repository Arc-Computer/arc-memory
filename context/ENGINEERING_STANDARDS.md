# Engineering Standards for Arc VS Code Extension Development

This document outlines the engineering standards and best practices to follow during the development of the Arc Memory VS Code Extension. Adherence to these standards is crucial for code quality, maintainability, collaboration, and alignment with open-source expectations.

## 1. Version Control (Git)

*   **Commits:**
    *   **Atomicity:** Each commit should represent a single, logical unit of work. Avoid large, monolithic commits.
    *   **Message Format:** Follow the **Conventional Commits** specification (https://www.conventionalcommits.org/). This enables automated changelog generation and improves history readability.
        *   Format: `type(optional scope): description`
        *   Example Types: `feat` (new feature), `fix` (bug fix), `chore` (build/tool changes), `docs` (documentation), `style` (formatting), `refactor`, `test`.
        *   Example: `feat(provider): implement initial hover card rendering`
        *   Example: `fix(rpc): handle JSON parsing errors from CLI`
    *   **Body/Footer:** Use the commit body for more detailed explanations if needed. Use footers for referencing issues (e.g., `Fixes #123`).
*   **Branching:**
    *   Work should be done on feature branches, named descriptively (e.g., `feat/hover-provider`, `fix/setup-check`).
    *   The `main` branch should be kept stable.
*   **Pull Requests (if applicable):**
    *   Even if working solo initially, simulate PRs for merging feature branches to `main`.
    *   PR descriptions should clearly explain the changes and reference relevant issues or ADRs.

## 2. Code Quality & Style (TypeScript)

*   **Language:** Use TypeScript. Leverage static typing to improve code robustness and clarity.
*   **Linting & Formatting:**
    *   Use **ESLint** for linting and **Prettier** for code formatting.
    *   Configuration files (`.eslintrc.js`, `.prettierrc.js`, `.prettierignore`) should be committed.
    *   Ensure code is free of linting errors and properly formatted before committing. Consider integrating via pre-commit hooks.
*   **Clarity & Readability:**
    *   Use meaningful names for variables, functions, classes, and files.
    *   Write simple, understandable logic. Avoid overly complex expressions or nesting.
    *   Follow the **DRY (Don't Repeat Yourself)** principle where appropriate.
*   **Modularity:**
    *   Adhere strictly to the project structure defined in `context/filestructure.md`.
    *   Keep components (classes, functions) focused on a single responsibility.
*   **Error Handling:**
    *   Implement robust error handling, especially around interactions with the VS Code API, file system operations, and external processes (`arc` CLI calls via `child_process`).
    *   Use `try...catch` blocks appropriately. Log errors effectively using `vscode.window.createOutputChannel` for user visibility or to the Debug Console during development.
*   **Asynchronous Code:**
    *   Use `async/await` for handling Promises. Avoid mixing `Promise.then()` and `async/await` unnecessarily.
*   **Comments:**
    *   Write comments to explain the *why* (rationale, intent, context), not the *what* (which should be clear from the code itself).
    *   Avoid obvious comments (e.g., `// increment counter`).
    *   Keep comments up-to-date with code changes.
*   **Dependencies:**
    *   Minimize external dependencies. Evaluate the need carefully before adding new ones.
    *   Keep dependencies updated (`npm update` or similar).

## 3. Architecture Decisions (ADRs)

*   **Purpose:** To document significant architectural decisions, their context, and consequences, ensuring transparency and knowledge sharing.
*   **When to Write an ADR:** Create an ADR for decisions that have a significant impact on the architecture, non-functional characteristics (performance, security), dependencies, or development approach. Examples include:
    *   Choosing the RPC mechanism (e.g., child process vs. HTTP server - *already decided for demo, but good example*).
    *   Selecting major libraries or frameworks (if any beyond standard VS Code/Node).
    *   Defining key data structures or interface contracts between major components.
    *   Significant refactoring decisions.
*   **Template:** Use a standard, simple template (inspired by Michael Nygard's format, see [https://github.com/joelparkerhenderson/architecture-decision-record]):
    *   **Title:** Short, descriptive title (e.g., `001-Use-Child-Process-for-SDK-RPC.md`).
    *   **Status:** Proposed, Accepted, Deprecated, Superseded.
    *   **Context:** What is the issue, background, constraints?
    *   **Decision:** What is the chosen solution?
    *   **Consequences:** What are the results (positive and negative) of this decision? What trade-offs were made?
*   **Location:** Store ADRs in a dedicated `docs/adr/` directory within the repository.
*   **Process (for Agent):**
    *   Identify when a decision meets the criteria for an ADR.
    *   Propose the ADR content based on the template.
    *   Seek review/acceptance from the user (PM/CTO) before finalizing the ADR status to 'Accepted'.
*   **Referencing:** Reference relevant ADRs in commit messages or code comments where the decision is implemented (e.g., `feat(rpc): implement RpcClient via child_process (see ADR-001)`).
*   **Best Practices:** Keep ADRs focused on a single decision. Reference separate design documents if extensive exploration was done. (See [https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/])

## 4. Documentation

*   **README.md:** Maintain a clear and comprehensive `README.md` covering project purpose, setup, usage, and contribution guidelines.
*   **Code Comments:** As per Section 2.
*   **Type Definitions:** Well-typed code using TypeScript serves as crucial documentation.
*   **ADRs:** Form a key part of the project's historical documentation (Section 3).

---

By adhering to these standards, we ensure the extension is built on a solid foundation, facilitating future development, maintenance, and potential contributions. 