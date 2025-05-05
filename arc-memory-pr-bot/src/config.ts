import { Context } from "probot";

/**
 * Configuration options for the Arc Memory PR Bot
 */
export interface BotConfig {
  /**
   * Enable or disable specific features
   */
  features: {
    /**
     * Show original design decisions
     */
    designDecisions: boolean;

    /**
     * Show predicted impact of changes
     */
    impactAnalysis: boolean;

    /**
     * Show proof that changes were properly tested
     */
    testVerification: boolean;

    /**
     * Use LLM for generating insights
     */
    useLLM: boolean;
  };

  /**
   * Risk score thresholds
   */
  riskThresholds: {
    /**
     * Threshold for low risk (0-100)
     */
    low: number;

    /**
     * Threshold for medium risk (0-100)
     */
    medium: number;

    /**
     * Threshold for high risk (0-100)
     */
    high: number;
  };

  /**
   * Comment formatting options
   */
  comment: {
    /**
     * Include risk score in the comment
     */
    includeRiskScore: boolean;

    /**
     * Include affected components in the comment
     */
    includeAffectedComponents: boolean;

    /**
     * Include test coverage in the comment
     */
    includeTestCoverage: boolean;

    /**
     * Include code snippets in the comment
     */
    includeCodeSnippets: boolean;
  };

  /**
   * LLM configuration options
   */
  llm: {
    /**
     * LLM provider to use (openai, anthropic)
     */
    provider: 'openai' | 'anthropic';

    /**
     * Model to use
     */
    model: string;

    /**
     * Temperature for sampling (0.0 to 1.0)
     */
    temperature: number;

    /**
     * Maximum tokens to generate
     */
    maxTokens: number;

    /**
     * Cache TTL in seconds
     */
    cacheTTL: number;
  };
}

/**
 * Default configuration for the Arc Memory PR Bot
 */
export const DEFAULT_CONFIG: BotConfig = {
  features: {
    designDecisions: true,
    impactAnalysis: true,
    testVerification: true,
    useLLM: true,
  },
  riskThresholds: {
    low: 40,
    medium: 70,
    high: 90,
  },
  comment: {
    includeRiskScore: true,
    includeAffectedComponents: true,
    includeTestCoverage: true,
    includeCodeSnippets: true,
  },
  llm: {
    provider: 'openai',
    model: 'gpt-4o',
    temperature: 0.7,
    maxTokens: 4000,
    cacheTTL: 3600,
  },
};

/**
 * Get the configuration for the bot
 * @param context Probot context
 * @returns Bot configuration
 */
export async function getConfig(context: Context): Promise<BotConfig> {
  try {
    // Try to load the configuration from the repository
    const config = await context.config<BotConfig>("arc-pr-bot.yml");

    // If no configuration is found, use the default configuration
    if (!config) {
      context.log.info("No configuration found, using default configuration");
      return DEFAULT_CONFIG;
    }

    // Merge the loaded configuration with the default configuration
    return {
      features: {
        ...DEFAULT_CONFIG.features,
        ...config.features,
      },
      riskThresholds: {
        ...DEFAULT_CONFIG.riskThresholds,
        ...config.riskThresholds,
      },
      comment: {
        ...DEFAULT_CONFIG.comment,
        ...config.comment,
      },
      llm: {
        ...DEFAULT_CONFIG.llm,
        ...config.llm,
      },
    };
  } catch (error) {
    // Log the error and use the default configuration
    context.log.error(`Error loading configuration: ${error}`);
    return DEFAULT_CONFIG;
  }
}

/**
 * Get the LLM configuration from environment variables
 * @returns LLM configuration
 */
export function getLLMConfigFromEnv(): BotConfig['llm'] {
  return {
    provider: (process.env.LLM_PROVIDER as 'openai' | 'anthropic') || 'openai',
    model: process.env.LLM_MODEL || 'gpt-4o',
    temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.7'),
    maxTokens: parseInt(process.env.LLM_MAX_TOKENS || '4000', 10),
    cacheTTL: parseInt(process.env.LLM_CACHE_TTL || '3600', 10),
  };
}
