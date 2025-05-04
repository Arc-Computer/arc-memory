import { Probot } from "probot";
import { getConfig } from "./config";

/**
 * Arc Memory PR Bot - Enhances pull requests with contextual information from the knowledge graph
 * @param {Probot} app - Probot's application instance
 */
export default (app: Probot) => {
  app.log.info("Arc Memory PR Bot is starting up!");

  // Handle pull request opened or synchronized events
  app.on(["pull_request.opened", "pull_request.synchronize"], async (context) => {
    const pr = context.payload.pull_request;
    app.log.info(`Received PR event: ${pr.title} (#${pr.number})`);

    try {
      // Load configuration
      const config = await getConfig(context);
      app.log.info(`Loaded configuration for PR #${pr.number}`, config);

      // Add a comment to the PR
      const comment = context.issue({
        body: `## Arc Memory PR Bot

👋 Thanks for the PR! I'm analyzing this change to provide context from the Arc Memory knowledge graph.

In the future, I'll provide information about:
${config.features.designDecisions ? '- Original design decisions behind the code\n' : ''}${config.features.impactAnalysis ? '- Predicted impact of changes\n' : ''}${config.features.testVerification ? '- Proof that changes were properly tested\n' : ''}
Stay tuned for more insights!`,
      });

      await context.octokit.issues.createComment(comment);
      app.log.info(`Added comment to PR #${pr.number}`);
    } catch (error) {
      app.log.error(`Error handling PR #${pr.number}: ${error}`);
    }
  });

  // Handle pull request review events
  app.on("pull_request_review.submitted", async (context) => {
    const review = context.payload.review;
    const pr = context.payload.pull_request;

    app.log.info(`Received PR review event for PR #${pr.number}`);
    app.log.info(`Review state: ${review.state}`);

    // In the future, we'll use this to update our analysis based on review feedback
  });

  // Handle push events
  app.on("push", async (context) => {
    const payload = context.payload;
    const repo = payload.repository.name;
    const owner = payload.repository.owner.login;
    const ref = payload.ref;

    app.log.info(`Received push event to ${ref} in ${owner}/${repo}`);
    app.log.info(`Number of commits: ${payload.commits.length}`);

    // In the future, we'll use this to update our knowledge graph
  });
};
