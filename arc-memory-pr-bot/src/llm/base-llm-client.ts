/**
 * Base LLM Client for the Arc Memory PR Bot
 * 
 * This abstract class defines the interface for LLM clients.
 * Concrete implementations will handle communication with specific LLM providers
 * like OpenAI GPT-4 or Anthropic Claude 3 Opus.
 */

import { Logger } from 'probot';
import NodeCache from 'node-cache';

/**
 * Response from an LLM
 */
export interface LLMResponse {
  /**
   * The generated text from the LLM
   */
  text: string;
  
  /**
   * The model used to generate the response
   */
  model: string;
  
  /**
   * The prompt tokens used
   */
  promptTokens?: number;
  
  /**
   * The completion tokens used
   */
  completionTokens?: number;
  
  /**
   * The total tokens used
   */
  totalTokens?: number;
}

/**
 * Options for LLM requests
 */
export interface LLMRequestOptions {
  /**
   * The maximum number of tokens to generate
   */
  maxTokens?: number;
  
  /**
   * The temperature for sampling (0.0 to 1.0)
   * Lower values make the output more deterministic
   */
  temperature?: number;
  
  /**
   * Whether to use the cache
   * Default: true
   */
  useCache?: boolean;
  
  /**
   * The time-to-live for the cache entry in seconds
   * Default: 3600 (1 hour)
   */
  cacheTTL?: number;
}

/**
 * Abstract base class for LLM clients
 */
export abstract class BaseLLMClient {
  protected logger: Logger;
  protected cache: NodeCache;
  
  /**
   * Create a new BaseLLMClient
   * @param logger Logger instance
   * @param cacheTTL Cache TTL in seconds (default: 3600 seconds)
   */
  constructor(logger: Logger, cacheTTL: number = 3600) {
    this.logger = logger;
    this.cache = new NodeCache({ stdTTL: cacheTTL, checkperiod: 120 });
  }
  
  /**
   * Generate a response from the LLM
   * @param prompt The prompt to send to the LLM
   * @param options Options for the request
   * @returns A promise that resolves to the LLM response
   */
  abstract generateResponse(prompt: string, options?: LLMRequestOptions): Promise<LLMResponse>;
  
  /**
   * Get the name of the LLM provider
   * @returns The name of the LLM provider
   */
  abstract getProviderName(): string;
  
  /**
   * Get the default model for the LLM provider
   * @returns The default model name
   */
  abstract getDefaultModel(): string;
  
  /**
   * Check if the LLM client is properly configured
   * @returns True if the client is properly configured, false otherwise
   */
  abstract isConfigured(): boolean;
  
  /**
   * Generate a cache key for a prompt and options
   * @param prompt The prompt
   * @param options The options
   * @returns A cache key
   */
  protected generateCacheKey(prompt: string, options?: LLMRequestOptions): string {
    // Create a hash of the prompt and options to use as a cache key
    const optionsStr = options ? JSON.stringify(options) : '';
    return `${this.getProviderName()}:${prompt.length}:${this.hashString(prompt + optionsStr)}`;
  }
  
  /**
   * Generate a simple hash of a string
   * @param str The string to hash
   * @returns A hash of the string
   */
  private hashString(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(16);
  }
  
  /**
   * Clear the cache
   */
  clearCache(): void {
    this.cache.flushAll();
    this.logger.info('LLM response cache cleared');
  }
}
