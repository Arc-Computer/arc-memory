import nock from "nock";
import { Probot, ProbotOctokit } from "probot";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, beforeEach, afterEach, test, expect, vi } from "vitest";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const privateKey = fs.readFileSync(
  path.join(__dirname, "fixtures/mock-cert.pem"),
  "utf-8",
);

// Load fixtures
const pullRequestOpenedPayload = JSON.parse(
  fs.readFileSync(path.join(__dirname, "fixtures/pull_request.opened.json"), "utf-8"),
);

describe("Arc Memory PR Bot", () => {
  let probot: any;

  // Mock the GraphService module
  vi.mock("../src/graph-service.js", () => {
    return {
      GraphService: vi.fn().mockImplementation(() => ({
        connect: vi.fn().mockResolvedValue(undefined),
        close: vi.fn().mockResolvedValue(undefined),
        findLinearTicketsForPR: vi.fn().mockResolvedValue([
          { id: 'issue:linear/ARC-42', title: 'Test Linear Ticket', state: 'completed', url: 'https://linear.app/test' }
        ]),
        findADRsForChangedFiles: vi.fn().mockResolvedValue([
          { id: 'adr:test', title: 'Test ADR', status: 'accepted', decision_makers: ['test-user'] }
        ]),
        getCommitHistoryForPR: vi.fn().mockResolvedValue([
          { id: 'commit:test', title: 'Test Commit', sha: 'abc123', files: ['test.ts'] }
        ]),
        findRelatedPRsForFile: vi.fn().mockResolvedValue([
          { id: 'pr:test', title: 'Test PR', number: 2, state: 'open', url: 'https://github.com/test' }
        ]),
        getStats: vi.fn().mockResolvedValue({ nodeCount: 100, edgeCount: 200 })
      }))
    };
  });

  // Mock the LLM client factory
  vi.mock("../src/llm/llm-client-factory.js", () => {
    return {
      LLMClientFactory: {
        createClientFromEnv: vi.fn().mockReturnValue({
          generateCompletion: vi.fn().mockResolvedValue("This is a mock LLM response")
        })
      }
    };
  });

  // Mock the PR Context Processor
  vi.mock("../src/llm/pr-context-processor.js", () => {
    return {
      RiskLevel: {
        LOW: "low",
        MEDIUM: "medium",
        HIGH: "high"
      },
      PRContextProcessor: vi.fn().mockImplementation(() => ({
        generateInsights: vi.fn().mockResolvedValue({
          designDecisions: {
            summary: "This is a test design decision",
            relatedADRs: [{ id: "ADR-001", title: "Test ADR", relevance: "Test relevance" }],
            relatedTickets: [{ id: "ABC-123", title: "Test ticket", relevance: "Test relevance" }],
            designPrinciples: ["Test principle"],
            explanation: "Test explanation"
          },
          impactAnalysis: {
            summary: "This is a test impact analysis",
            riskScore: { score: 30, level: "low", explanation: "Test explanation" },
            affectedComponents: [{ name: "TestComponent", impact: "Test impact" }],
            potentialIssues: ["Test issue"],
            recommendations: ["Test recommendation"]
          },
          testVerification: {
            summary: "This is a test verification",
            testCoverage: { percentage: 90, assessment: "Test assessment" },
            testGaps: ["Test gap"],
            recommendations: ["Test recommendation"]
          }
        })
      }))
    };
  });

  // Import the app after mocking
  let myProbotApp: any;

  beforeEach(async () => {
    // Dynamically import the app after mocking
    myProbotApp = (await import("../src/index.js")).default;

    nock.disableNetConnect();
    probot = new Probot({
      appId: 123,
      privateKey,
      // disable request throttling and retries for testing
      Octokit: ProbotOctokit.defaults({
        retry: { enabled: false },
        throttle: { enabled: false },
      }),
    });
    // Load our app into probot
    probot.load(myProbotApp);
  });

  test("creates a comment when a pull request is opened", async () => {
    // Mock the repository-specific configuration with useLLM: true
    nock("https://api.github.com")
      .get("/repos/Arc-Computer/arc-memory/contents/.github%2Farc-pr-bot.yml")
      .reply(200, {
        content: Buffer.from(JSON.stringify({
          features: {
            designDecisions: true,
            impactAnalysis: true,
            testVerification: true,
            useLLM: true
          }
        })).toString('base64'),
        encoding: 'base64'
      });

    // Mock the files API
    nock("https://api.github.com")
      .get("/repos/Arc-Computer/arc-memory/pulls/1/files")
      .reply(200, [
        {
          filename: "src/index.ts",
          additions: 10,
          deletions: 5,
          patch: "@@ -1,5 +1,10 @@\n import { Probot } from 'probot';\n+import { getConfig } from './config';\n function myFunction() {\n-  return true;\n+  return false;\n }"
        },
        {
          filename: "src/config.ts",
          additions: 5,
          deletions: 2,
          patch: "@@ -1,3 +1,6 @@\n export const config = {\n-  enabled: true\n+  enabled: false,\n+  features: {\n+    useLLM: true\n+  }\n };"
        }
      ]);

    const mock = nock("https://api.github.com")
      // Test that we correctly return a test token
      .post("/app/installations/12345678/access_tokens")
      .reply(200, {
        token: "test",
        permissions: {
          pull_requests: "write",
          contents: "read",
          metadata: "read",
        },
      })

      // Test that initial comment is posted
      .post("/repos/Arc-Computer/arc-memory/issues/1/comments", (body: any) => {
        // Check that the comment body contains our expected text
        expect(body.body).toContain("Arc Memory PR Bot");
        expect(body.body).toContain("Thanks for the PR!");
        expect(body.body).toContain("Original design decisions");
        expect(body.body).toContain("Predicted impact");
        expect(body.body).toContain("Proof that changes were properly tested");
        return true;
      })
      .reply(200)

      // Test that LLM-generated comment is posted
      .post("/repos/Arc-Computer/arc-memory/issues/1/comments", (body: any) => {
        // Check that the comment body contains our expected text from the mocked LLM response
        expect(body.body).toContain("The original design decisions behind the code");
        expect(body.body).toContain("The predicted impact of the change");
        expect(body.body).toContain("Proof that the change was properly tested");
        expect(body.body).toContain("This is a test design decision");
        expect(body.body).toContain("This is a test impact analysis");
        expect(body.body).toContain("This is a test verification");
        return true;
      })
      .reply(200);

    // Receive a webhook event
    await probot.receive({ name: "pull_request", payload: pullRequestOpenedPayload });

    // Check that all expected API calls were made
    expect(mock.pendingMocks()).toStrictEqual([]);
  }, 30000);

  afterEach(() => {
    nock.cleanAll();
    nock.enableNetConnect();
  });
});

// For more information about testing with Jest see:
// https://facebook.github.io/jest/

// For more information about using TypeScript in your tests, Jest recommends:
// https://github.com/kulshekhar/ts-jest

// For more information about testing with Nock see:
// https://github.com/nock/nock
