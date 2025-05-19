# Telemetry in Arc Memory

## 1. Overview

Arc Memory is committed to user privacy. We understand the importance of keeping your data, especially your codebase and development activities, secure and private.

To help us improve Arc Memory, we offer an **entirely opt-in** telemetry system. This system is **disabled by default**. If you choose to opt-in, Arc Memory will collect anonymous data about usage patterns and common errors. This information is invaluable for us to understand how the tool is used, identify areas for improvement, and prioritize bug fixes.

## 2. How to Opt-In/Opt-Out

Telemetry settings are stored in the Arc Memory configuration file, located at `~/.arc/config.json` (where `~` represents your user home directory).

*   **To Opt-In**:
    You need to manually edit (or create if it doesn't exist) the `config.json` file and set the `telemetry.enabled` field to `true`.

    Example `~/.arc/config.json` for opting in:
    ```json
    {
      "telemetry": {
        "enabled": true,
        "installation_id": "a_randomly_generated_uuid_will_appear_here",
        "current_session_id": null
      }
      // ... other configurations might be present
    }
    ```

*   **To Opt-Out (or Confirm Opt-Out Status)**:
    Ensure the `telemetry.enabled` field in `~/.arc/config.json` is set to `false`. This is the default state.

    Example `~/.arc/config.json` for opting out:
    ```json
    {
      "telemetry": {
        "enabled": false,
        "installation_id": "a_randomly_generated_uuid_if_telemetry_was_ever_enabled",
        "current_session_id": null
      }
      // ... other configurations might be present
    }
    ```

If the `~/.arc/config.json` file does not exist, or if the `telemetry` section is missing, Arc Memory will automatically create it with `telemetry.enabled` set to `false` the first time it runs, ensuring telemetry remains disabled unless you explicitly enable it.

## 3. What Data is Collected (If Opted-In)

We want to be completely transparent about what data is collected if you choose to opt-in. **Crucially, no personally identifiable information (PII), code content, file contents, repository names, specific file paths, or query text is ever collected.** Our focus is on anonymous usage patterns.

If telemetry is enabled, the following types of anonymous data are collected:

*   **Anonymous Installation ID**:
    *   A randomly generated UUID (`installation_id`) is created and stored in your `~/.arc/config.json`.
    *   This helps distinguish usage data from different Arc Memory installations without identifying the individual user or machine.
*   **Session Events**:
    *   Anonymous start and end markers for "investigation sessions" (events named `session_start`, `session_end`).
    *   These are associated with a temporary, randomly generated session UUID (`current_session_id` in your config, which changes per session).
    *   This helps us understand typical session lengths for certain tasks (e.g., for Mean Time To Resolution - MTTR analytics on aggregate).
*   **Command Usage**:
    *   **Name of the CLI command used**: For example, `build`, `query`, `auth status`.
    *   **Command success/failure**: Whether the command completed successfully or resulted in an error.
    *   **Error type (if an error occurred)**: The class name of the error (e.g., `FileNotFoundError`, `BuildError`, `JiraAuthError`). **The actual error message, which might contain sensitive path information or details, is NOT collected.**
    *   **Non-sensitive command-line arguments/options**: We may collect information about which flags are used (e.g., `--include-github`, `--verbose`, `--llm-enhancement`), but **values associated with arguments that might contain sensitive information (like paths, query strings, or specific IDs) are not collected.**
*   **Arc Memory Version**:
    *   The version of the `arc-memory` package you are using (e.g., `0.7.5`).
*   **Operating System Information (Anonymous)**:
    *   Type of operating system (e.g., "Linux", "Darwin" for macOS, "Windows").
    *   CPU architecture (e.g., "amd64", "arm64").

We **do not** track your IP address (PostHog is configured with `disable_geoip=True`).

## 4. Why Telemetry is Useful

Collecting this anonymous data, if you choose to share it, helps the Arc Memory development team in several ways:

*   **Understand Feature Usage**: Identifies which features and commands are most popular and which might be underutilized, guiding development focus.
*   **Identify Common Errors**: Helps pinpoint frequent errors or points of friction, allowing us to prioritize fixes and improvements.
*   **Improve Performance**: Provides insights into the performance characteristics of different commands and operations in real-world scenarios.
*   **Enhance User Experience**: By understanding common workflows, we can make the tool more intuitive and efficient.

Your participation, while entirely voluntary, directly contributes to making Arc Memory a better tool for everyone.

## 5. Data Storage and Third Parties

If you opt-in to telemetry, the anonymized data described above is sent to **PostHog**.
*   **PostHog Website**: [https://posthog.com](https://posthog.com)

PostHog is an open-source product analytics platform that we use for aggregating and analyzing this anonymous usage data. This helps us visualize trends, understand usage patterns, and ultimately, improve Arc Memory. We do not share this data with any other third parties.
