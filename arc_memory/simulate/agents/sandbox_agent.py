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
    from smolagents import CodeAgent, LiteLLMModel
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
        model_name: Model name (default: "gpt-4.1-2025-04-14")
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
        if not api_key and llm_provider == "openai":
            raise ValueError("OpenAI API key not found in environment variables.")

        # Create the model
        model = LiteLLMModel(
            model_id=model_name,
            api_key=api_key
        )

        # Get E2B API key for sandbox execution
        e2b_api_key = os.environ.get("E2B_API_KEY", "")

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
        # Create the agent prompt
        agent_prompt = f"""
You are a system reliability engineer tasked with running a fault injection simulation.

You have been provided with a simulation manifest at {manifest_path}.
The manifest contains information about the scenario, severity, affected services, and paths to the diff and causal graph.

Your task is to:
1. Read the manifest
2. Set up a k3d cluster
3. Deploy Chaos Mesh
4. Apply a chaos experiment based on the scenario and severity
5. Collect metrics before and after the experiment
6. Return the results

Please follow these steps:
1. Read the manifest file
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
