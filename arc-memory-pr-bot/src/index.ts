import { Probot } from "probot";
import { getConfig, BotConfig } from "./config";
import { GraphService } from "./graph-service";

/**
 * Generates the comment body for the PR based on the configuration.
 * @param {BotConfig} config - The configuration object.
 * @param {Object} context - Optional context information from the knowledge graph.
 * @returns {string} - The constructed comment body.
 */
function generateCommentBody(
  config: BotConfig,
  context?: {
    linearTickets?: any[],
    adrs?: any[],
    commits?: any[],
    relatedPRs?: any[]
  }
): string {
  // If no context is provided, show the initial message
  if (!context) {
    const features = [];
    if (config.features.designDecisions) {
      features.push('- Original design decisions behind the code');
    }
    if (config.features.impactAnalysis) {
      features.push('- Predicted impact of changes');
    }
    if (config.features.testVerification) {
      features.push('- Proof that changes were properly tested');
    }

    return `## Arc Memory PR Bot

👋 Thanks for the PR! I'm analyzing this change to provide context from the Arc Memory knowledge graph.

In the future, I'll provide information about:
${features.join('\n')}

Stay tuned for more insights!`;
  }

  // If context is provided, generate a more detailed comment
  let comment = `## Arc Memory PR Bot Analysis\n\n`;

  // Add design decisions section if enabled
  if (config.features.designDecisions && context.adrs && context.adrs.length > 0) {
    comment += `### Original design decisions behind the code\n\n`;
    comment += `This code is related to the following architectural decisions:\n\n`;

    context.adrs.forEach(adr => {
      comment += `- **${adr.title}** (${adr.status})\n`;
      if (adr.decision_makers && adr.decision_makers.length > 0) {
        comment += `  Decision makers: ${adr.decision_makers.join(', ')}\n`;
      }
    });

    comment += `\n`;
  }

  // Add impact analysis section if enabled
  if (config.features.impactAnalysis) {
    comment += `### Predicted impact of changes\n\n`;

    if (context.relatedPRs && context.relatedPRs.length > 0) {
      comment += `This change may affect code that was previously modified in:\n\n`;
      context.relatedPRs.slice(0, 5).forEach(pr => {
        comment += `- [#${pr.number}: ${pr.title}](${pr.url})\n`;
      });
      comment += `\n`;
    }

    if (context.linearTickets && context.linearTickets.length > 0) {
      comment += `Related Linear tickets:\n\n`;
      context.linearTickets.forEach(ticket => {
        comment += `- [${ticket.id.split('/')[1]}: ${ticket.title}](${ticket.url}) (${ticket.state})\n`;
      });
      comment += `\n`;
    }
  }

  // Add test verification section if enabled
  if (config.features.testVerification && context.commits && context.commits.length > 0) {
    comment += `### Proof that changes were properly tested\n\n`;
    comment += `This PR includes ${context.commits.length} commits:\n\n`;

    context.commits.forEach(commit => {
      comment += `- ${commit.title} (${commit.sha.substring(0, 7)})\n`;
      if (commit.files && commit.files.length > 0) {
        comment += `  Modified files: ${commit.files.length}\n`;
      }
    });
  }

  return comment;
}

/**
 * Arc Memory PR Bot - Enhances pull requests with contextual information from the knowledge graph
 * @param {Probot} app - Probot's application instance
 */
export default (app: Probot) => {
  app.log.info("Arc Memory PR Bot is starting up!");

  // Create a GraphService instance
  const graphService = new GraphService(app.log);

  // Handle pull request opened or synchronized events
  app.on(["pull_request.opened", "pull_request.synchronize"], async (context) => {
    const pr = context.payload.pull_request;
    const repo = context.payload.repository;
    app.log.info(`Received PR event: ${pr.title} (#${pr.number})`);

    try {
      // Load configuration
      const config = await getConfig(context);
      app.log.info(`Loaded configuration for PR #${pr.number}`, config);

      // Add an initial comment to let the user know we're analyzing the PR
      const initialComment = context.issue({
        body: generateCommentBody(config),
      });
      await context.octokit.issues.createComment(initialComment);
      app.log.info(`Added initial comment to PR #${pr.number}`);

      // Connect to the knowledge graph
      try {
        await graphService.connect();
        app.log.info(`Connected to knowledge graph database`);

        // Get the list of files changed in the PR
        const filesResponse = await context.octokit.pulls.listFiles({
          owner: repo.owner.login,
          repo: repo.name,
          pull_number: pr.number,
        });

        const changedFiles = filesResponse.data.map(file => file.filename);
        app.log.info(`PR #${pr.number} changes ${changedFiles.length} files`);

        // Query the knowledge graph for context
        const [linearTickets, adrs, commits] = await Promise.all([
          graphService.findLinearTicketsForPR(pr.number, repo.owner.login, repo.name),
          graphService.findADRsForChangedFiles(changedFiles),
          graphService.getCommitHistoryForPR(pr.number, repo.owner.login, repo.name),
        ]);

        // Find related PRs for the changed files
        const relatedPRPromises = changedFiles.map(file =>
          graphService.findRelatedPRsForFile(file)
        );
        const relatedPRsArrays = await Promise.all(relatedPRPromises);

        // Flatten and deduplicate the related PRs
        const relatedPRsMap = new Map();
        relatedPRsArrays.flat().forEach(pr => {
          if (!relatedPRsMap.has(pr.id)) {
            relatedPRsMap.set(pr.id, pr);
          }
        });
        const relatedPRs = Array.from(relatedPRsMap.values());

        // Filter out the current PR from related PRs
        const filteredRelatedPRs = relatedPRs.filter(
          relatedPR => relatedPR.number !== pr.number
        );

        app.log.info(`Found ${linearTickets.length} Linear tickets, ${adrs.length} ADRs, ${commits.length} commits, and ${filteredRelatedPRs.length} related PRs`);

        // Generate a detailed comment with the context
        const detailedComment = context.issue({
          body: generateCommentBody(config, {
            linearTickets,
            adrs,
            commits,
            relatedPRs: filteredRelatedPRs,
          }),
        });

        await context.octokit.issues.createComment(detailedComment);
        app.log.info(`Added detailed comment to PR #${pr.number}`);
      } catch (graphError) {
        app.log.error(`Error querying knowledge graph: ${graphError}`);

        // Add a comment to let the user know there was an error
        const errorComment = context.issue({
          body: `## Arc Memory PR Bot Error

I encountered an error while querying the knowledge graph: ${graphError.message}

Please make sure the knowledge graph is built and up-to-date by running \`arc build\`.`,
        });

        await context.octokit.issues.createComment(errorComment);
      } finally {
        // Close the database connection
        await graphService.close();
      }
    } catch (error) {
      app.log.error(`Error handling PR #${pr.number}: ${error}`);

      // Add a comment to let the user know there was an error
      const errorComment = context.issue({
        body: `## Arc Memory PR Bot Error

I encountered an error while processing this PR: ${error}

Please check the logs for more details.`,
      });

      try {
        await context.octokit.issues.createComment(errorComment);
      } catch (commentError) {
        app.log.error(`Error adding error comment: ${commentError}`);
      }
    }
  });

  // Handle pull request review events
  app.on("pull_request_review.submitted", async (context) => {
    const review = context.payload.review;
    const pr = context.payload.pull_request;
    const repo = context.payload.repository;

    app.log.info(`Received PR review event for PR #${pr.number}`);
    app.log.info(`Review state: ${review.state}`);

    // Only process approved reviews for now
    if (review.state === 'approved') {
      try {
        // Load configuration
        const config = await getConfig(context);

        // Connect to the knowledge graph
        try {
          await graphService.connect();
          app.log.info(`Connected to knowledge graph database for PR review`);

          // Get the list of files changed in the PR
          const filesResponse = await context.octokit.pulls.listFiles({
            owner: repo.owner.login,
            repo: repo.name,
            pull_number: pr.number,
          });

          const changedFiles = filesResponse.data.map(file => file.filename);

          // Query the knowledge graph for context
          const [linearTickets, adrs] = await Promise.all([
            graphService.findLinearTicketsForPR(pr.number, repo.owner.login, repo.name),
            graphService.findADRsForChangedFiles(changedFiles),
          ]);

          // Add a comment with approval context
          if (linearTickets.length > 0 || adrs.length > 0) {
            const approvalComment = context.issue({
              body: `## Arc Memory PR Bot - Approval Context

This PR has been approved by @${review.user.login}.

${linearTickets.length > 0 ? `
### Related Linear Tickets
${linearTickets.map(ticket => `- [${ticket.id.split('/')[1]}: ${ticket.title}](${ticket.url}) (${ticket.state})`).join('\n')}
` : ''}

${adrs.length > 0 ? `
### Related Architectural Decisions
${adrs.map(adr => `- **${adr.title}** (${adr.status})`).join('\n')}
` : ''}

This context is provided to help with the merge decision.`,
            });

            await context.octokit.issues.createComment(approvalComment);
            app.log.info(`Added approval context comment to PR #${pr.number}`);
          }
        } catch (graphError) {
          app.log.error(`Error querying knowledge graph for PR review: ${graphError}`);
        } finally {
          // Close the database connection
          await graphService.close();
        }
      } catch (error) {
        app.log.error(`Error handling PR review for #${pr.number}: ${error}`);
      }
    }
  });

  // Handle push events
  app.on("push", async (context) => {
    const payload = context.payload;
    const repo = payload.repository.name;
    const owner = payload.repository.owner.login;
    const ref = payload.ref;

    app.log.info(`Received push event to ${ref} in ${owner}/${repo}`);
    app.log.info(`Number of commits: ${payload.commits.length}`);

    // Only process pushes to main/master branch
    if (ref === 'refs/heads/main' || ref === 'refs/heads/master') {
      try {
        // Connect to the knowledge graph
        try {
          await graphService.connect();
          app.log.info(`Connected to knowledge graph database for push event`);

          // Get database statistics before processing
          const stats = await graphService.getStats();
          app.log.info(`Knowledge graph stats: ${stats.nodeCount} nodes, ${stats.edgeCount} edges`);

          // For each commit, find files that were modified
          const modifiedFiles = new Set<string>();

          payload.commits.forEach(commit => {
            // Add all modified files to the set
            commit.added.forEach(file => modifiedFiles.add(file));
            commit.modified.forEach(file => modifiedFiles.add(file));
            commit.removed.forEach(file => modifiedFiles.add(file));
          });

          app.log.info(`Push affects ${modifiedFiles.size} unique files`);

          // Find open PRs that might be affected by these changes
          const openPRsResponse = await context.octokit.pulls.list({
            owner,
            repo,
            state: 'open',
          });

          // For each open PR, check if it modifies any of the same files
          for (const openPR of openPRsResponse.data) {
            const filesResponse = await context.octokit.pulls.listFiles({
              owner,
              repo,
              pull_number: openPR.number,
            });

            const prFiles = filesResponse.data.map(file => file.filename);

            // Check for overlap between PR files and modified files
            const overlap = prFiles.filter(file => modifiedFiles.has(file));

            if (overlap.length > 0) {
              app.log.info(`Push may affect PR #${openPR.number} (${overlap.length} overlapping files)`);

              // Add a comment to the PR
              const comment = {
                owner,
                repo,
                issue_number: openPR.number,
                body: `## Arc Memory PR Bot - Potential Conflicts

Recent changes to the \`${ref.replace('refs/heads/', '')}\` branch may affect this PR.

${overlap.length} files modified in this PR were also modified in the recent push:
${overlap.slice(0, 5).map(file => `- \`${file}\``).join('\n')}${overlap.length > 5 ? `\n- ... and ${overlap.length - 5} more` : ''}

You may want to rebase this PR to incorporate these changes.`,
              };

              await context.octokit.issues.createComment(comment);
              app.log.info(`Added conflict warning comment to PR #${openPR.number}`);
            }
          }
        } catch (graphError) {
          app.log.error(`Error querying knowledge graph for push event: ${graphError}`);
        } finally {
          // Close the database connection
          await graphService.close();
        }
      } catch (error) {
        app.log.error(`Error handling push event: ${error}`);
      }
    }
  });
};
