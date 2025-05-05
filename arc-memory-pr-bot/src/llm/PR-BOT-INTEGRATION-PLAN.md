# PR Bot Integration Plan

## Overview

This plan outlines how to integrate the PR Context Processor with the main PR Bot code to generate insights for real PRs.

## Current Architecture

The current PR Bot architecture consists of:

1. **index.ts**: The main entry point that sets up the Probot app and registers event handlers
2. **context-generator.ts**: Generates context for PRs by querying the knowledge graph
3. **graph-service.ts**: Provides access to the knowledge graph database

## Integration Steps

### 1. Update index.ts

Update the PR event handlers to use the PR Context Processor:

```typescript
import { PRContextProcessor } from './llm/pr-context-processor';
import { LLMClientFactory } from './llm/llm-client-factory';
import { CommentFormatter } from './llm/comment-formatter';

export = (app: Probot) => {
  app.on(['pull_request.opened', 'pull_request.synchronize'], async (context) => {
    // Existing code to get PR context
    const contextGenerator = new ContextGenerator(graphService);
    const prContext = await contextGenerator.generateContext(context);

    // New code to generate insights using the PR Context Processor
    const llmClient = LLMClientFactory.createClient();
    const prContextProcessor = new PRContextProcessor(llmClient);

    try {
      const insights = await prContextProcessor.generateInsights(prContext);

      // Format the insights as a comment
      const commentFormatter = new CommentFormatter();
      const comment = commentFormatter.formatComment(insights);

      // Post the comment on the PR
      await context.octokit.issues.createComment({
        owner: context.payload.repository.owner.login,
        repo: context.payload.repository.name,
        issue_number: context.payload.pull_request.number,
        body: comment,
      });
    } catch (error) {
      // Handle errors and use fallbacks
      app.log.error(`Error generating insights: ${error}`);

      // Use fallback mechanism
      const fallbackComment = prContextProcessor.generateFallbackInsights(prContext);

      // Post the fallback comment
      await context.octokit.issues.createComment({
        owner: context.payload.repository.owner.login,
        repo: context.payload.repository.name,
        issue_number: context.payload.pull_request.number,
        body: fallbackComment,
      });
    }
  });
};
```

### 2. Create Configuration for LLM API Keys

Add configuration for LLM API keys and settings:

```typescript
// src/config.ts
export interface LLMConfig {
  provider: 'openai' | 'anthropic';
  apiKey: string;
  model: string;
  temperature: number;
  maxTokens: number;
}

export function getLLMConfig(): LLMConfig {
  return {
    provider: process.env.LLM_PROVIDER as 'openai' | 'anthropic' || 'openai',
    apiKey: process.env.OPENAI_API_KEY || process.env.ANTHROPIC_API_KEY || '',
    model: process.env.LLM_MODEL || 'gpt-4o',
    temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.7'),
    maxTokens: parseInt(process.env.LLM_MAX_TOKENS || '4000', 10),
  };
}
```

### 3. Update the PR Context Processor

Enhance the PR Context Processor to handle real PR data:

```typescript
// src/llm/pr-context-processor.ts
import { PRContext } from '../types';
import { BaseLLMClient } from './base-llm-client';

export class PRContextProcessor {
  constructor(private llmClient: BaseLLMClient) {}

  async generateInsights(prContext: PRContext): Promise<PRInsights> {
    // Generate insights using the LLM
  }

  generateFallbackInsights(prContext: PRContext): string {
    // Generate fallback insights when the LLM is unavailable
  }
}
```

### 4. Create the Comment Formatter

Create a new class to format the insights as a GitHub comment:

```typescript
// src/llm/comment-formatter.ts
import { PRInsights } from './pr-context-processor';

export class CommentFormatter {
  /**
   * Format the insights as Markdown for a GitHub comment
   * @param insights The PR insights to format
   * @param prTitle The PR title (optional)
   * @returns The formatted comment as Markdown
   */
  formatComment(insights: PRInsights, prTitle?: string): string {
    // Format the header
    // Format the three sections (design decisions, impact analysis, test verification)
    // Return the formatted comment
  }

  /**
   * Format a code diff
   * @param diff The diff to format
   * @returns The formatted diff
   */
  formatCodeDiff(diff: string): string {
    // Format the code diff as a collapsible section
  }
}
```

### 5. Add Error Handling and Fallbacks

Enhance error handling and add fallback mechanisms:

```typescript
// src/llm/pr-context-processor.ts
export class PRContextProcessor {
  // ...

  generateFallbackInsights(prContext: PRContext): string {
    // Generate a simple comment with basic PR information
    return `
# Arc Memory PR Bot

Sorry, I couldn't generate detailed insights for this PR due to an error.

## Basic PR Information

- Title: ${prContext.title}
- Author: ${prContext.author}
- Changed Files: ${prContext.changedFiles.length}

## Related Linear Tickets

${prContext.linearTickets.map(ticket => `- ${ticket.title} (${ticket.id})`).join('\n')}

## Related ADRs

${prContext.adrs.map(adr => `- ${adr.title}`).join('\n')}
    `;
  }
}
```

## Testing Plan

1. Create unit tests for the integration
2. Test with real PRs from the repository
3. Verify that the insights are generated correctly
4. Verify that the comments are formatted correctly
5. Verify that error handling and fallbacks work correctly
