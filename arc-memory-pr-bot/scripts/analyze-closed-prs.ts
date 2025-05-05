/**
 * Script to analyze closed PRs and test the PR Context Processor
 * 
 * This script fetches closed PRs from the repository, extracts their content,
 * and feeds it to the PR Context Processor to generate insights.
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
import { PRContextProcessor } from '../src/llm/pr-context-processor.js';
import { LLMClientFactory } from '../src/llm/llm-client-factory.js';
import { CommentFormatter } from '../src/llm/comment-formatter.js';
import { DEFAULT_CONFIG } from '../src/config.js';

// Load environment variables
config();

// Create a logger
const logger = {
  info: (message: string, ...args: any[]) => console.log(`[INFO] ${message}`, ...args),
  warn: (message: string, ...args: any[]) => console.warn(`[WARN] ${message}`, ...args),
  error: (message: string, ...args: any[]) => console.error(`[ERROR] ${message}`, ...args),
  debug: (message: string, ...args: any[]) => console.debug(`[DEBUG] ${message}`, ...args),
};

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
    const graphService = new GraphService(logger);
    await graphService.connect();
    logger.info('Connected to knowledge graph database');
    
    // Create a mock context
    const context = {
      prNumber,
      prTitle: pr.title,
      prBody: pr.body,
      changedFiles: files,
      relatedEntities: {
        linearTickets: await graphService.findLinearTicketsForPR(pr.title, pr.body, pr.head.ref),
        adrs: await graphService.findADRsForChangedFiles(files.map(file => file.filename)),
        commits: await graphService.getCommitHistoryForPR(prNumber.toString()),
        relatedPRs: await Promise.all(files.map(file => graphService.findRelatedPRsForFile(file.filename))).then(results => results.flat()),
      },
    };
    
    // Initialize the LLM client
    const llmClient = LLMClientFactory.createClientFromEnv(logger);
    
    // Initialize the PR Context Processor
    const prContextProcessor = new PRContextProcessor(llmClient, logger);
    
    // Generate insights
    logger.info('Generating insights...');
    const insights = await prContextProcessor.generateInsights(context);
    
    // Format the insights
    const commentFormatter = new CommentFormatter();
    const comment = commentFormatter.formatComment(insights, pr.title);
    
    // Extract relevant code diffs for visualization
    const diffSnippets = extractRelevantDiffs(files, insights);
    
    // Add code diff visualizations
    let finalComment = comment;
    if (diffSnippets.length > 0) {
      finalComment += '\n\n## Code Changes\n\n';
      diffSnippets.forEach(snippet => {
        finalComment += commentFormatter.formatCodeDiff(snippet.diff) + '\n\n';
      });
    }
    
    // Save the insights to a file
    const outputDir = path.join(process.cwd(), 'output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir);
    }
    
    const outputFile = path.join(outputDir, `pr-${prNumber}-insights.md`);
    fs.writeFileSync(outputFile, finalComment);
    logger.info(`Insights saved to ${outputFile}`);
    
    // Close the database connection
    await graphService.close();
    
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
 * Extract relevant code diffs from the PR for visualization
 * @param changedFiles The files changed in the PR
 * @param insights The insights generated by the LLM
 * @returns An array of diff snippets
 */
function extractRelevantDiffs(changedFiles: any[], insights: any) {
  const snippets: { filename: string; diff: string; relevance: string }[] = [];
  
  // Extract affected components from impact analysis
  const affectedComponents = insights.impactAnalysis.affectedComponents || [];
  
  // Extract files with test gaps from test verification
  const testGaps = insights.testVerification.testGaps || [];
  
  // Process each changed file
  for (const file of changedFiles) {
    // Skip files without patches
    if (!file.patch) continue;
    
    // Check if this file is part of an affected component
    const isAffectedComponent = affectedComponents.some((component: any) => 
      file.filename.includes(component.name)
    );
    
    // Check if this file is related to test gaps
    const isRelatedToTestGaps = testGaps.some((gap: string) => 
      gap.toLowerCase().includes(file.filename.toLowerCase())
    );
    
    // Add the file if it's relevant
    if (isAffectedComponent || isRelatedToTestGaps) {
      snippets.push({
        filename: file.filename,
        diff: file.patch,
        relevance: isAffectedComponent 
          ? `Related to affected component: ${affectedComponents.find((c: any) => file.filename.includes(c.name))?.name}`
          : `Related to test gap: ${testGaps.find((g: string) => g.toLowerCase().includes(file.filename.toLowerCase()))}`
      });
    }
  }
  
  // If no relevant diffs were found, include the most significant changes
  if (snippets.length === 0 && changedFiles.length > 0) {
    // Sort files by the number of changes (additions + deletions)
    const sortedFiles = [...changedFiles].sort((a, b) => 
      (b.additions + b.deletions) - (a.additions + a.deletions)
    );
    
    // Add the top 3 most changed files
    for (let i = 0; i < Math.min(3, sortedFiles.length); i++) {
      if (sortedFiles[i].patch) {
        snippets.push({
          filename: sortedFiles[i].filename,
          diff: sortedFiles[i].patch,
          relevance: `Significant change (${sortedFiles[i].additions} additions, ${sortedFiles[i].deletions} deletions)`
        });
      }
    }
  }
  
  return snippets;
}

// Run the main function
main().catch(error => {
  logger.error('Unhandled error:', error);
  process.exit(1);
});
