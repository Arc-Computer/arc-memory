# LLM Integration for Arc Memory PR Bot

This module provides integration with Large Language Models (LLMs) for the Arc Memory PR Bot. It enables the bot to generate AI-powered insights about pull requests based on the knowledge graph data.

## Components

- **BaseLLMClient**: Abstract base class defining the common interface for LLM clients
- **OpenAIClient**: Implementation for OpenAI GPT-4
- **LLMClientFactory**: Factory class to create the appropriate client based on configuration

## Usage

### Creating an LLM Client

```typescript
import { LLMClientFactory, LLMProvider } from './llm';

// Create a client using the factory
const llmClient = LLMClientFactory.createClient(logger, {
  provider: LLMProvider.OPENAI,
  openai: {
    apiKey: 'your-api-key',
    model: 'gpt-4', // Optional, defaults to 'gpt-4'
    organization: 'your-org-id', // Optional
  },
  cacheTTL: 3600, // Optional, defaults to 3600 seconds (1 hour)
});

// Or create a client from environment variables
const llmClient = LLMClientFactory.createClientFromEnv(logger);
```

### Generating Responses

```typescript
import { LLMRequestOptions } from './llm';

// Define options for the request
const options: LLMRequestOptions = {
  maxTokens: 1000, // Optional, defaults to 1000
  temperature: 0.7, // Optional, defaults to 0.7
  useCache: true, // Optional, defaults to true
  cacheTTL: 3600, // Optional, defaults to 3600 seconds (1 hour)
};

// Generate a response
try {
  const response = await llmClient.generateResponse('Your prompt here', options);
  console.log(response.text);
} catch (error) {
  console.error('Error generating response:', error);
}
```

## Environment Variables

The following environment variables can be used to configure the LLM client:

- `LLM_PROVIDER`: The LLM provider to use (default: 'openai')
- `LLM_CACHE_TTL`: The cache TTL in seconds (default: 3600)
- `OPENAI_API_KEY`: The API key for OpenAI (required when using OpenAI)
- `OPENAI_MODEL`: The model to use for OpenAI (default: 'gpt-4')
- `OPENAI_ORGANIZATION`: The organization ID for OpenAI (optional)

## Error Handling

The LLM client includes built-in error handling for common issues:

- Rate limit errors: Automatically retries with exponential backoff
- API errors: Throws descriptive error messages
- Configuration errors: Validates configuration before making requests

## Caching

Responses are cached by default to improve performance and reduce API costs. The cache key is based on the prompt and options, and the cache TTL can be configured.

To clear the cache:

```typescript
llmClient.clearCache();
```

## Future Enhancements

- Add support for Anthropic Claude 3 Opus
- Implement streaming responses
- Add support for function calling
- Improve prompt engineering with chain-of-thought reasoning
