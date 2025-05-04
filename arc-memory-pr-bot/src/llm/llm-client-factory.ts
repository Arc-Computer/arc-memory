/**
 * LLM Client Factory for the Arc Memory PR Bot
 *
 * This factory creates LLM clients based on configuration.
 * It supports different LLM providers like OpenAI and Anthropic.
 */

import { Logger } from 'probot';
import { BaseLLMClient } from './base-llm-client.js';
import { OpenAIClient, OpenAIClientConfig } from './openai-client.js';

/**
 * LLM Provider types
 */
export enum LLMProvider {
  OPENAI = 'openai',
  // ANTHROPIC = 'anthropic', // To be implemented later
}

/**
 * LLM Client Factory configuration
 */
export interface LLMClientFactoryConfig {
  /**
   * The LLM provider to use
   */
  provider: LLMProvider;

  /**
   * OpenAI configuration (required if provider is OPENAI)
   */
  openai?: OpenAIClientConfig;

  /**
   * Anthropic configuration (required if provider is ANTHROPIC)
   * To be implemented later
   */
  // anthropic?: AnthropicClientConfig;

  /**
   * The cache TTL in seconds (default: 3600)
   */
  cacheTTL?: number;
}

/**
 * LLM Client Factory
 */
export class LLMClientFactory {
  /**
   * Create an LLM client based on configuration
   * @param logger Logger instance
   * @param config LLM client factory configuration
   * @returns An LLM client
   */
  static createClient(logger: Logger, config: LLMClientFactoryConfig): BaseLLMClient {
    switch (config.provider) {
      case LLMProvider.OPENAI:
        if (!config.openai) {
          throw new Error('OpenAI configuration is required when provider is OPENAI');
        }
        return new OpenAIClient(logger, {
          ...config.openai,
          cacheTTL: config.cacheTTL || config.openai.cacheTTL,
        });

      // To be implemented later
      // case LLMProvider.ANTHROPIC:
      //   if (!config.anthropic) {
      //     throw new Error('Anthropic configuration is required when provider is ANTHROPIC');
      //   }
      //   return new AnthropicClient(logger, {
      //     ...config.anthropic,
      //     cacheTTL: config.cacheTTL || config.anthropic.cacheTTL,
      //   });

      default:
        throw new Error(`Unsupported LLM provider: ${config.provider}`);
    }
  }

  /**
   * Create an LLM client from environment variables
   * @param logger Logger instance
   * @returns An LLM client
   */
  static createClientFromEnv(logger: Logger): BaseLLMClient {
    // Determine the provider from environment variables
    const provider = process.env.LLM_PROVIDER as LLMProvider || LLMProvider.OPENAI;

    // Create the configuration based on the provider
    const config: LLMClientFactoryConfig = {
      provider,
      cacheTTL: parseInt(process.env.LLM_CACHE_TTL || '3600', 10),
    };

    // Add provider-specific configuration
    if (provider === LLMProvider.OPENAI) {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey) {
        throw new Error('OPENAI_API_KEY environment variable is required when using OpenAI');
      }

      config.openai = {
        apiKey,
        model: process.env.OPENAI_MODEL || 'gpt-4o',
        organization: process.env.OPENAI_ORGANIZATION,
      };
    }
    // To be implemented later
    // else if (provider === LLMProvider.ANTHROPIC) {
    //   const apiKey = process.env.ANTHROPIC_API_KEY;
    //   if (!apiKey) {
    //     throw new Error('ANTHROPIC_API_KEY environment variable is required when using Anthropic');
    //   }
    //
    //   config.anthropic = {
    //     apiKey,
    //     model: process.env.ANTHROPIC_MODEL || 'claude-3-opus-20240229',
    //   };
    // }

    // Create and return the client
    return LLMClientFactory.createClient(logger, config);
  }
}
