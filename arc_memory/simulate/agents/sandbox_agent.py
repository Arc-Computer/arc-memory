"""Agent for sandbox testing in Arc Memory simulation.

This module provides an agent for running simulations in sandbox environments.
"""

import os
import json
import time
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


def create_sandbox_agent(
    llm_provider: str = "openai",
    model_name: str = "gpt-4o",
    executor_type: str = "e2b"
) -> Optional[CodeAgent]:
    """Create an agent for sandbox testing.

    Args:
        llm_provider: LLM provider (default: "openai")
        model_name: Model name (default: "gpt-4o")
        executor_type: Executor type (default: "e2b")

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
            def __init__(self, client, model_id, temperature=0.2, max_tokens=4000):
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
            temperature=0.2,  # Lower temperature for more deterministic outputs
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
            tools=[],  # No tools needed for sandbox testing
            executor_kwargs={"api_key": e2b_api_key} if executor_type == "e2b" else None
        )

        logger.info(f"Created sandbox agent with {llm_provider} {model_name}")
        return agent
    except Exception as e:
        logger.error(f"Error creating sandbox agent: {e}")
        raise RuntimeError(f"Error creating sandbox agent: {e}")


def run_sandbox_tests_with_agent(
    agent: CodeAgent,
    manifest_path: str,
    duration_seconds: int = 300,
    metrics_interval: int = 30,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """Run sandbox tests using the sandbox agent.

    Args:
        agent: CodeAgent instance
        manifest_path: Path to the simulation manifest file
        duration_seconds: Duration of the simulation in seconds (default: 300)
        metrics_interval: Interval between metrics collection in seconds (default: 30)
        progress_callback: Callback function for progress updates (optional)

    Returns:
        Dictionary containing the test results

    Raises:
        RuntimeError: If the tests fail
    """
    # Create a progress reporter
    from arc_memory.simulate.utils.progress import create_progress_reporter
    report_progress = create_progress_reporter(progress_callback)

    # Update progress
    report_progress("Running simulation in sandbox environment", 50)

    logger.info(f"Running sandbox tests with manifest: {manifest_path}")

    try:
        # Read the manifest content to include in the prompt
        try:
            with open(manifest_path, 'r') as f:
                manifest_content = f.read()
        except Exception as e:
            logger.warning(f"Error reading manifest file: {e}. Will use placeholder.")
            manifest_content = '{"scenario": "network_latency", "severity": 50, "affected_services": []}'

        # Create the agent prompt with manifest content included
        agent_prompt = f"""
You are a system reliability engineer tasked with running a fault injection simulation.

Here is the simulation manifest content:
```json
{manifest_content}
```

The manifest contains information about the scenario, severity, affected services, and paths to the diff and causal graph.

Your task is to:
1. Parse the manifest content provided above
2. Set up a k3d cluster
3. Deploy Chaos Mesh
4. Apply a chaos experiment based on the scenario and severity
5. Collect metrics before and after the experiment
6. Return the results

Please follow these steps:
1. Parse the manifest content from the JSON provided above
2. Import the necessary modules from arc_memory.simulate.code_interpreter
3. Create a simulation environment
4. Set up the k3d cluster
5. Deploy Chaos Mesh
6. Generate a chaos experiment manifest based on the scenario and severity
7. Apply the chaos experiment
8. Collect initial metrics
9. Wait for {duration_seconds} seconds
10. Collect final metrics
11. Clean up resources
12. Return the results as a JSON object

The simulation should run for {duration_seconds} seconds.

IMPORTANT: The manifest content is already provided in this prompt. Do not try to read it from a file.
"""

        # Run the agent
        start_time = time.time()
        agent_result = agent.run(agent_prompt)  # Timeout is handled by the agent internally
        end_time = time.time()

        # Update progress periodically during the experiment
        elapsed = end_time - start_time
        progress = min(int(50 + (elapsed / (duration_seconds + 120)) * 45), 95)
        report_progress(f"Completed sandbox tests in {int(elapsed)}s", progress)

        # Parse the agent result
        try:
            simulation_results = json.loads(agent_result.output)
        except json.JSONDecodeError:
            # Try to extract JSON from the output
            import re
            json_match = re.search(r'```json\n(.*?)\n```', agent_result.output, re.DOTALL)
            if json_match:
                simulation_results = json.loads(json_match.group(1))
            else:
                raise ValueError("Agent output does not contain valid JSON")

        # Add the agent output to the results
        simulation_results["agent_output"] = agent_result.output

        # Update progress
        report_progress("Successfully ran simulation", 100)

        logger.info("Successfully ran sandbox tests")
        return simulation_results
    except Exception as e:
        logger.error(f"Error running sandbox tests: {e}")

        # Update progress
        report_progress(f"Error running sandbox tests: {str(e)[:50]}...", 100)

        # Generate mock results
        mock_results = {
            "error": str(e),
            "is_mock": True,
            "experiment_name": "mock-experiment",
            "duration_seconds": duration_seconds,
            "initial_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time() - duration_seconds
            },
            "final_metrics": {
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3,
                "timestamp": time.time()
            },
            "timestamp": time.time()
        }

        return mock_results
