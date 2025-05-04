import nock from "nock";
import myProbotApp from "../src/index.js";
import { Probot, ProbotOctokit } from "probot";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, beforeEach, afterEach, test, expect } from "vitest";

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

  beforeEach(() => {
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

      // Test that a comment is posted
      .post("/repos/Arc-Computer/arc-memory/issues/1/comments", (body: any) => {
        // Check that the comment body contains our expected text
        expect(body.body).toContain("Arc Memory PR Bot");
        expect(body.body).toContain("Thanks for the PR!");
        expect(body.body).toContain("Original design decisions");
        expect(body.body).toContain("Predicted impact");
        expect(body.body).toContain("Proof that changes were properly tested");
        return true;
      })
      .reply(200);

    // Receive a webhook event
    await probot.receive({ name: "pull_request", payload: pullRequestOpenedPayload });

    expect(mock.pendingMocks()).toStrictEqual([]);
  });

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
