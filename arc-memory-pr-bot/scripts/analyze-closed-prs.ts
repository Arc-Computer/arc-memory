/**
 * Script to extract PR information for analysis
 *
 * This script fetches closed PRs from the repository and extracts their content
 * for manual analysis. It also connects to the knowledge graph to retrieve
 * related entities.
 *
 * Usage:
 * npm run build
 * node dist/scripts/analyze-closed-prs.js <pr-number>
 */

import { Octokit } from '@octokit/rest';
import { config } from 'dotenv';
import fs from 'fs';
import path from 'path';
import { GraphService } from '../src/graph-service.js';

// Load environment variables
config({ path: '.env.analyze' });

// Create a logger
const logger = console;

// Create an Octokit instance
const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN,
});

// Repository information
const owner = 'Arc-Computer';
const repo = 'arc-memory';

/**
 * Main function
 */
async function main() {
  try {
    // Get PR number from command line arguments
    const prNumber = process.argv[2] ? parseInt(process.argv[2], 10) : null;

    if (!prNumber) {
      logger.info('No PR number provided. Fetching recent closed PRs...');
      await listClosedPRs();
      return;
    }

    logger.info(`Analyzing PR #${prNumber}...`);

    // Fetch PR details
    const pr = await fetchPR(prNumber);
    logger.info(`PR Title: ${pr.title}`);
    logger.info(`PR Description: ${pr.body}`);

    // Fetch PR files
    const files = await fetchPRFiles(prNumber);
    logger.info(`PR changes ${files.length} files`);

    // Connect to the knowledge graph
    const dbPath = process.env.DB_PATH || '/Users/jarrodbarnes/.arc/graph.db';
    logger.info(`Connecting to knowledge graph at ${dbPath}`);

    const graphService = new GraphService(logger, dbPath);
    try {
      await graphService.connect();
      logger.info('Connected to knowledge graph database');

      // Fetch related entities from the knowledge graph
      const linearTickets = await graphService.findLinearTicketsForPR(prNumber, owner, repo);
      logger.info(`Found ${linearTickets.length} related Linear tickets`);

      const adrs = await graphService.findADRsForChangedFiles(files.map(file => file.filename));
      logger.info(`Found ${adrs.length} related ADRs`);

      const commits = await graphService.getCommitHistoryForPR(prNumber, owner, repo);
      logger.info(`Found ${commits.length} related commits`);

      const relatedPRs = await Promise.all(files.map(file =>
        graphService.findRelatedPRsForFile(file.filename)
      )).then(results => {
        // Flatten and deduplicate
        const prMap = new Map();
        results.flat().forEach(pr => prMap.set(pr.id, pr));
        return Array.from(prMap.values());
      });
      logger.info(`Found ${relatedPRs.length} related PRs`);

      // Create output directory
      const outputDir = path.join(process.cwd(), 'output');
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir);
      }

      // Save PR information to a file
      const prInfo = {
        number: pr.number,
        title: pr.title,
        body: pr.body,
        author: pr.user.login,
        created_at: pr.created_at,
        merged_at: pr.merged_at,
        base: pr.base.ref,
        head: pr.head.ref,
        files: files.map(file => ({
          filename: file.filename,
          status: file.status,
          additions: file.additions,
          deletions: file.deletions,
          patch: file.patch
        })),
        relatedEntities: {
          linearTickets: linearTickets.map(ticket => ({
            id: ticket.id,
            title: ticket.title,
            state: ticket.state,
            url: ticket.url
          })),
          adrs: adrs.map(adr => ({
            id: adr.id,
            title: adr.title,
            status: adr.status,
            decision_makers: adr.decision_makers
          })),
          commits: commits.map(commit => ({
            id: commit.id,
            title: commit.title,
            author: commit.author,
            sha: commit.sha
          })),
          relatedPRs: relatedPRs.map(relPr => ({
            id: relPr.id,
            number: relPr.number,
            title: relPr.title,
            state: relPr.state,
            url: relPr.url
          }))
        }
      };

      const outputFile = path.join(outputDir, `pr-${prNumber}-info.json`);
      fs.writeFileSync(outputFile, JSON.stringify(prInfo, null, 2));
      logger.info(`PR information saved to ${outputFile}`);

      // Generate a markdown summary
      const markdownSummary = generateMarkdownSummary(prInfo);
      const markdownFile = path.join(outputDir, `pr-${prNumber}-summary.md`);
      fs.writeFileSync(markdownFile, markdownSummary);
      logger.info(`PR summary saved to ${markdownFile}`);

      // Close the database connection
      await graphService.close();
      logger.info('Database connection closed');
    } catch (error) {
      logger.error(`Error connecting to knowledge graph: ${error}`);
    }

  } catch (error) {
    logger.error('Error:', error);
  }
}

/**
 * Fetch a PR from GitHub
 * @param prNumber The PR number
 * @returns The PR details
 */
async function fetchPR(prNumber: number) {
  const { data } = await octokit.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  return data;
}

/**
 * Fetch PR files from GitHub
 * @param prNumber The PR number
 * @returns The PR files
 */
async function fetchPRFiles(prNumber: number) {
  const { data } = await octokit.pulls.listFiles({
    owner,
    repo,
    pull_number: prNumber,
  });

  return data;
}

/**
 * List recent closed PRs
 */
async function listClosedPRs() {
  const { data } = await octokit.pulls.list({
    owner,
    repo,
    state: 'closed',
    sort: 'updated',
    direction: 'desc',
    per_page: 10,
  });

  logger.info('Recent closed PRs:');
  data.forEach(pr => {
    logger.info(`#${pr.number}: ${pr.title}`);
  });

  logger.info('\nTo analyze a specific PR, run:');
  logger.info('node dist/scripts/analyze-closed-prs.js <pr-number>');
}

/**
 * Generate a markdown summary of the PR
 * @param prInfo The PR information
 * @returns A markdown summary
 */
function generateMarkdownSummary(prInfo: any): string {
  // Format the PR information as markdown
  let markdown = `# PR #${prInfo.number}: ${prInfo.title}\n\n`;

  // Add PR metadata
  markdown += `- **Author:** ${prInfo.author}\n`;
  markdown += `- **Created:** ${new Date(prInfo.created_at).toLocaleString()}\n`;
  markdown += `- **Merged:** ${prInfo.merged_at ? new Date(prInfo.merged_at).toLocaleString() : 'Not merged'}\n`;
  markdown += `- **Branch:** \`${prInfo.head}\` → \`${prInfo.base}\`\n\n`;

  // Add PR description
  markdown += `## Description\n\n${prInfo.body || 'No description provided.'}\n\n`;

  // Add related entities
  if (prInfo.relatedEntities) {
    // Add Linear tickets
    if (prInfo.relatedEntities.linearTickets && prInfo.relatedEntities.linearTickets.length > 0) {
      markdown += `## Related Linear Tickets\n\n`;
      prInfo.relatedEntities.linearTickets.forEach((ticket: any) => {
        markdown += `- [${ticket.id.split('/')[1]}: ${ticket.title}](${ticket.url}) (${ticket.state})\n`;
      });
      markdown += `\n`;
    }

    // Add ADRs
    if (prInfo.relatedEntities.adrs && prInfo.relatedEntities.adrs.length > 0) {
      markdown += `## Related ADRs\n\n`;
      prInfo.relatedEntities.adrs.forEach((adr: any) => {
        markdown += `- **${adr.title}** (${adr.status})\n`;
        if (adr.decision_makers && adr.decision_makers.length > 0) {
          markdown += `  Decision makers: ${adr.decision_makers.join(', ')}\n`;
        }
      });
      markdown += `\n`;
    }

    // Add commits
    if (prInfo.relatedEntities.commits && prInfo.relatedEntities.commits.length > 0) {
      markdown += `## Commits\n\n`;
      prInfo.relatedEntities.commits.forEach((commit: any) => {
        markdown += `- ${commit.title} (${commit.sha.substring(0, 7)}) by ${commit.author}\n`;
      });
      markdown += `\n`;
    }

    // Add related PRs
    if (prInfo.relatedEntities.relatedPRs && prInfo.relatedEntities.relatedPRs.length > 0) {
      markdown += `## Related PRs\n\n`;
      prInfo.relatedEntities.relatedPRs.forEach((relPr: any) => {
        markdown += `- [#${relPr.number}: ${relPr.title}](${relPr.url}) (${relPr.state})\n`;
      });
      markdown += `\n`;
    }
  }

  // Add file changes
  markdown += `## Files Changed\n\n`;
  markdown += `Total: ${prInfo.files.length} files changed, ${prInfo.files.reduce((sum: number, file: any) => sum + file.additions, 0)} additions, ${prInfo.files.reduce((sum: number, file: any) => sum + file.deletions, 0)} deletions\n\n`;

  // List files
  markdown += `| File | Changes | Additions | Deletions |\n`;
  markdown += `|------|---------|-----------|----------|\n`;

  prInfo.files.forEach((file: any) => {
    markdown += `| \`${file.filename}\` | ${file.status} | ${file.additions} | ${file.deletions} |\n`;
  });

  markdown += `\n## Diffs\n\n`;

  // Add diffs for each file
  prInfo.files.forEach((file: any) => {
    if (file.patch) {
      markdown += `### ${file.filename}\n\n`;
      markdown += "```diff\n";
      markdown += file.patch;
      markdown += "\n```\n\n";
    }
  });

  return markdown;
}

// Run the main function
main().catch(error => {
  logger.error('Unhandled error:', error);
  process.exit(1);
});
