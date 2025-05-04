/**
 * OpenAI Client for the Arc Memory PR Bot
 *
 * This class implements the BaseLLMClient interface for OpenAI's GPT models.
 * It handles communication with the OpenAI API, including authentication,
 * request formatting, and response parsing.
 */

import { Logger } from 'probot';
import { BaseLLMClient, LLMResponse, LLMRequestOptions } from './base-llm-client.js';
import OpenAI from 'openai';

/**
 * OpenAI Client configuration
 */
export interface OpenAIClientConfig {
  /**
   * The API key for OpenAI
   */
  apiKey: string;

  /**
   * The model to use (default: gpt-4)
   */
  model?: string;

  /**
   * The organization ID (optional)
   */
  organization?: string;

  /**
   * The cache TTL in seconds (default: 3600)
   */
  cacheTTL?: number;
}

/**
 * OpenAI Client for the Arc Memory PR Bot
 */
export class OpenAIClient extends BaseLLMClient {
  private client: OpenAI;
  private model: string;
  private apiKey: string;

  /**
   * Create a new OpenAIClient
   * @param logger Logger instance
   * @param config OpenAI client configuration
   */
  constructor(logger: Logger, config: OpenAIClientConfig) {
    super(logger, config.cacheTTL);

    this.apiKey = config.apiKey;
    this.model = config.model || 'gpt-4o';

    // Initialize the OpenAI client
    this.client = new OpenAI({
      apiKey: this.apiKey,
      organization: config.organization,
    });

    this.logger.info(`Initialized OpenAI client with model: ${this.model}`);
  }

  /**
   * Generate a response from the OpenAI API
   * @param prompt The prompt to send to the API
   * @param options Options for the request
   * @returns A promise that resolves to the LLM response
   */
  async generateResponse(prompt: string, options?: LLMRequestOptions): Promise<LLMResponse> {
    // Check if the client is configured
    if (!this.isConfigured()) {
      throw new Error('OpenAI client is not properly configured. API key is missing.');
    }

    // Check if we should use the cache
    const useCache = options?.useCache !== false;
    if (useCache) {
      const cacheKey = this.generateCacheKey(prompt, options);
      const cachedResponse = this.cache.get<LLMResponse>(cacheKey);

      if (cachedResponse) {
        this.logger.debug('Using cached OpenAI response');
        return cachedResponse;
      }
    }

    try {
      // Set up the request parameters
      const model = this.model;
      const maxTokens = options?.maxTokens || 1000;
      const temperature = options?.temperature !== undefined ? options.temperature : 0.7;

      this.logger.debug(`Sending request to OpenAI API with model: ${model}, maxTokens: ${maxTokens}, temperature: ${temperature}`);

      // Make the API request with exponential backoff for rate limits
      const response = await this.makeRequestWithRetry(prompt, model, maxTokens, temperature);

      // Parse the response
      const result: LLMResponse = {
        text: response.choices[0]?.message?.content || '',
        model: response.model,
        promptTokens: response.usage?.prompt_tokens,
        completionTokens: response.usage?.completion_tokens,
        totalTokens: response.usage?.total_tokens,
      };

      // Cache the response if caching is enabled
      if (useCache) {
        const cacheKey = this.generateCacheKey(prompt, options);
        const cacheTTL = options?.cacheTTL || 3600;
        this.cache.set(cacheKey, result, cacheTTL);
      }

      return result;
    } catch (error) {
      this.logger.error(`Error generating response from OpenAI: ${error}`);
      throw new Error(`Failed to generate response from OpenAI: ${error}`);
    }
  }

  /**
   * Make a request to the OpenAI API with exponential backoff for rate limits
   * @param prompt The prompt to send
   * @param model The model to use
   * @param maxTokens The maximum number of tokens to generate
   * @param temperature The temperature for sampling
   * @returns The API response
   */
  private async makeRequestWithRetry(
    prompt: string,
    model: string,
    maxTokens: number,
    temperature: number,
    retries: number = 3,
    initialDelay: number = 1000
  ): Promise<OpenAI.Chat.Completions.ChatCompletion> {
    let delay = initialDelay;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        // First try to use the newer Responses API if the model supports it
        if (model.includes('gpt-4o') || model.includes('gpt-4.1')) {
          try {
            const response = await this.client.responses.create({
              model,
              input: prompt,
              max_tokens: maxTokens,
              temperature,
            });

            // Convert the response to match the Chat Completions API format
            return {
              id: response.id,
              object: 'chat.completion',
              created: Math.floor(Date.now() / 1000),
              model: response.model,
              choices: [
                {
                  index: 0,
                  message: {
                    role: 'assistant',
                    content: response.output_text || '',
                  },
                  finish_reason: 'stop',
                }
              ],
              usage: {
                prompt_tokens: response.usage?.input_tokens || 0,
                completion_tokens: response.usage?.output_tokens || 0,
                total_tokens: (response.usage?.input_tokens || 0) + (response.usage?.output_tokens || 0),
              }
            } as OpenAI.Chat.Completions.ChatCompletion;
          } catch (responseError: any) {
            // If the Responses API fails, fall back to the Chat Completions API
            this.logger.warn(`Responses API failed, falling back to Chat Completions API: ${responseError.message}`);
          }
        }

        // Fall back to the Chat Completions API
        return await this.client.chat.completions.create({
          model,
          messages: [{ role: 'user', content: prompt }],
          max_tokens: maxTokens,
          temperature,
        });
      } catch (error: any) {
        // If we've used all our retries, or it's not a rate limit error, rethrow
        if (attempt === retries || !this.isRateLimitError(error)) {
          throw error;
        }

        // Log the rate limit error
        this.logger.warn(`Rate limit exceeded, retrying in ${delay}ms (attempt ${attempt + 1}/${retries})`);

        // Wait for the delay period
        await new Promise(resolve => setTimeout(resolve, delay));

        // Exponential backoff with jitter
        delay = delay * 2 + Math.random() * 200;
      }
    }

    // This should never be reached due to the throw in the catch block
    throw new Error('Failed to generate response after retries');
  }

  /**
   * Check if an error is a rate limit error
   * @param error The error to check
   * @returns True if it's a rate limit error, false otherwise
   */
  private isRateLimitError(error: any): boolean {
    return (
      error.status === 429 ||
      (error.error?.type === 'rate_limit_exceeded') ||
      (error.message && error.message.includes('rate limit'))
    );
  }

  /**
   * Get the name of the LLM provider
   * @returns The name of the LLM provider
   */
  getProviderName(): string {
    return 'openai';
  }

  /**
   * Get the default model for the LLM provider
   * @returns The default model name
   */
  getDefaultModel(): string {
    return 'gpt-4o';
  }

  /**
   * Check if the OpenAI client is properly configured
   * @returns True if the client is properly configured, false otherwise
   */
  isConfigured(): boolean {
    return !!this.apiKey && this.apiKey.length > 0;
  }
}
