"""Agent for diff analysis in Arc Memory simulation.

This module provides an agent for analyzing diffs and identifying affected services.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Check if Smol Agents is available
try:
    from smolagents import CodeAgent
    HAS_SMOL_AGENTS = True
except ImportError:
    HAS_SMOL_AGENTS = False


def create_diff_agent(
    llm_provider: str = "openai",
    model_name: str = "gpt-4o",
    executor_type: str = "local"
) -> Optional[CodeAgent]:
    """Create an agent for diff analysis.

    Args:
        llm_provider: LLM provider (default: "openai")
        model_name: Model name (default: "gpt-4o")
        executor_type: Executor type (default: "local")

    Returns:
        CodeAgent instance or None if Smol Agents is not available

    Raises:
        RuntimeError: If the agent cannot be created
    """
    # Check if Smol Agents is available
    if not HAS_SMOL_AGENTS:
        logger.error("Smol Agents is not available. Please install it with 'pip install smolagents'.")
        return None

    try:
        # Get the API key from environment variables
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key and llm_provider == "openai":
            # Import the environment utilities
            from arc_memory.simulate.utils.env import get_api_key

            # Get the API key from the environment or provided value
            api_key = get_api_key(api_key, "OPENAI_API_KEY")

            # Set the API key in the environment
            os.environ["OPENAI_API_KEY"] = api_key

        # Import OpenAI directly
        from openai import OpenAI

        # Create a client with the API key
        openai_client = OpenAI(api_key=api_key)

        # Create a wrapper for the OpenAI client that matches the LiteLLMModel interface
        class OpenAIModelWrapper:
            def __init__(self, client, model_id, temperature=0.1, max_tokens=4000):
                self.client = client
                self.model_id = model_id
                self.temperature = temperature
                self.max_tokens = max_tokens

            def __call__(self, messages, **kwargs):
                # Convert messages to the format expected by OpenAI
                formatted_messages = []
                for message in messages:
                    if isinstance(message["content"], list):
                        # Handle multi-modal content
                        formatted_messages.append({
                            "role": message["role"],
                            "content": message["content"]
                        })
                    else:
                        # Handle text-only content
                        formatted_messages.append({
                            "role": message["role"],
                            "content": message["content"]
                        })

                # Make the API call
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=formatted_messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )

                # Return a response object that matches the LiteLLMModel interface
                from smolagents.models import ChatMessage
                return ChatMessage(
                    role="assistant",
                    content=response.choices[0].message.content,
                    raw=response
                )

        # Create the model with the API key
        model = OpenAIModelWrapper(
            client=openai_client,
            model_id=model_name,
            temperature=0.1,  # Lower temperature for more deterministic outputs
            max_tokens=4000   # Ensure we have enough tokens for the response
        )

        # Get E2B API key for sandbox execution
        from arc_memory.simulate.utils.env import get_api_key
        try:
            e2b_api_key = get_api_key(None, "E2B_API_KEY")
        except ValueError:
            logger.warning("E2B API key not found, using empty string")
            e2b_api_key = ""

        # Create the agent with proper sandbox configuration
        agent = CodeAgent(
            model=model,
            executor_type=executor_type,
            tools=[],  # No tools needed for diff analysis
            executor_kwargs={"api_key": e2b_api_key} if executor_type == "e2b" else None
        )

        logger.info(f"Created diff agent with {llm_provider} {model_name}")
        return agent
    except Exception as e:
        logger.error(f"Error creating diff agent: {e}")
        raise RuntimeError(f"Error creating diff agent: {e}")


def analyze_diff_with_agent(
    agent: CodeAgent,
    diff_data: Dict[str, Any],
    db_path: str
) -> List[str]:
    """Analyze a diff using the diff agent.

    Args:
        agent: CodeAgent instance
        diff_data: Dictionary containing the diff data
        db_path: Path to the knowledge graph database

    Returns:
        List of affected service names

    Raises:
        RuntimeError: If the analysis fails
    """
    logger.info("Analyzing diff with agent")

    try:
        # Save the diff data to a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(diff_data, f, indent=2)
            diff_path = f.name

        # Create the agent prompt
        agent_prompt = f"""
You are a system reliability engineer tasked with analyzing a Git diff to identify affected services.

You have been provided with a diff file at {diff_path}.
The diff contains information about the files that have been changed.

Your task is to:
1. Read the diff file
2. Analyze the file paths to identify which services are affected
3. Return a list of affected service names

Please follow these steps:
1. Read the diff file
2. Extract the file paths from the diff
3. Analyze the file paths to identify services
4. Return a JSON array of service names

A service name is typically derived from the directory structure. For example:
- src/auth/server.js -> auth
- services/payment/api.py -> payment
- apps/frontend/components/Button.tsx -> frontend

If you cannot identify a service name, use the top-level directory name.
"""

        # Run the agent
        agent_result = agent.run(agent_prompt)

        # Parse the agent result
        try:
            affected_services = json.loads(agent_result.output)
            if not isinstance(affected_services, list):
                raise ValueError("Agent output is not a list")
        except json.JSONDecodeError:
            # Try to extract JSON from the output
            import re
            json_match = re.search(r'```json\n(.*?)\n```', agent_result.output, re.DOTALL)
            if json_match:
                affected_services = json.loads(json_match.group(1))
                if not isinstance(affected_services, list):
                    raise ValueError("Agent output is not a list")
            else:
                raise ValueError("Agent output does not contain valid JSON")

        # Clean up the temporary file
        os.unlink(diff_path)

        logger.info(f"Identified {len(affected_services)} affected services")
        return affected_services
    except Exception as e:
        logger.error(f"Error analyzing diff with agent: {e}")

        # Fall back to static analysis
        from arc_memory.simulate.diff import analyze_changes

        logger.info("Falling back to static analysis")
        return analyze_changes(diff_data, db_path)
