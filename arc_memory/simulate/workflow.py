"""Main workflow orchestration module for Arc Memory simulation using Smol Agents.

This module provides functions for orchestrating the simulation workflow using
Smol Agents.
"""

import os
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.utils.progress import create_progress_reporter

logger = get_logger(__name__)

# Check if Smol Agents is available
try:
    from smolagents import CodeAgent
    HAS_SMOL_AGENTS = True
except ImportError:
    HAS_SMOL_AGENTS = False


def create_simulation_agent(
    llm_provider: str = "openai",
    model_name: str = "gpt-4o",
    executor_type: str = "e2b",
    api_key: Optional[str] = None
) -> Union[CodeAgent, None]:
    """Create a simulation agent using Smol Agents.

    Args:
        llm_provider: LLM provider (default: "openai")
        model_name: Model name (default: "gpt-4o")
        executor_type: Executor type (default: "e2b")
        api_key: API key for the LLM provider (optional)

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
            tools=[],  # No tools needed for workflow orchestration
            executor_kwargs={"api_key": e2b_api_key} if executor_type == "e2b" else None,
            additional_authorized_imports=["os", "json", "time", "base64", "subprocess", "pathlib"]
        )

        logger.info(f"Created simulation agent with {llm_provider} {model_name}")
        return agent
    except Exception as e:
        logger.error(f"Error creating simulation agent: {e}")
        raise RuntimeError(f"Error creating simulation agent: {e}")


def run_simulation_workflow(
    rev_range: str,
    scenario: str = "network_latency",
    severity: int = 50,
    timeout: int = 600,
    repo_path: Optional[str] = None,
    db_path: Optional[str] = None,
    diff_data: Optional[Dict[str, Any]] = None,
    use_memory: bool = False,
    model_name: str = "gpt-4o",
    progress_callback: Optional[Callable[[str, int], None]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Run the simulation workflow using Smol Agents.

    Args:
        rev_range: Git revision range
        scenario: Fault scenario ID (default: "network_latency")
        severity: Severity level (0-100) (default: 50)
        timeout: Timeout in seconds (default: 600)
        repo_path: Path to the repository (default: current directory)
        db_path: Path to the knowledge graph database (default: .arc/graph.db)
        diff_data: Pre-loaded diff data (optional)
        use_memory: Whether to use memory integration (default: False)
        model_name: Model name to use for LLM (default: "gpt-4o")
        progress_callback: Callback function for progress updates (optional)
        verbose: Whether to enable verbose output (default: False)

    Returns:
        Dictionary containing the simulation results

    Raises:
        RuntimeError: If the simulation fails
    """
    # Create a progress reporter
    report_progress = create_progress_reporter(progress_callback)

    # Update progress
    report_progress("Initializing simulation workflow", 5)

    logger.info(f"Running simulation workflow for {rev_range}")

    try:
        # Set default values
        if repo_path is None:
            repo_path = os.getcwd()

        if db_path is None:
            db_path = os.path.join(os.path.expanduser("~"), ".arc", "graph.db")

        # Create the simulation agent
        report_progress(f"Creating simulation agent with model {model_name}", 10)

        # Get the API key from environment variables
        from arc_memory.simulate.utils.env import get_api_key
        api_key = get_api_key(None, "OPENAI_API_KEY")

        agent = create_simulation_agent(model_name=model_name, api_key=api_key)

        if agent is None:
            raise RuntimeError("Failed to create simulation agent")

        # Extract the diff if not provided
        if diff_data is None:
            report_progress(f"Extracting diff for range: {rev_range}", 15)

            # Import here to avoid circular imports
            from arc_memory.simulate.diff import extract_diff

            diff_data = extract_diff(rev_range, repo_path)

        # Analyze the diff to identify affected services
        report_progress("Analyzing diff to identify affected services", 20)

        # Import here to avoid circular imports
        from arc_memory.simulate.diff import analyze_changes

        affected_services = analyze_changes(diff_data, db_path)

        # Build the causal graph
        report_progress("Building causal graph from knowledge graph", 30)

        # Import here to avoid circular imports
        from arc_memory.simulate.causal_utils import build_causal_graph

        causal_graph = build_causal_graph(db_path)

        # Generate the simulation manifest
        report_progress(f"Generating simulation manifest for scenario: {scenario}", 40)

        # Create a temporary directory for the simulation
        import tempfile
        sim_dir = Path(tempfile.mkdtemp(prefix="arc_sim_"))

        # Save the diff data to a file
        diff_path = sim_dir / "diff.json"
        with open(diff_path, 'w') as f:
            json.dump(diff_data, f, indent=2)

        # Save the causal graph to a file
        causal_path = sim_dir / "causal.json"
        with open(causal_path, 'w') as f:
            json.dump(causal_graph, f, indent=2)

        # Create the manifest
        manifest = {
            "scenario": scenario,
            "severity": severity,
            "affected_services": affected_services,
            "diff_path": str(diff_path),
            "causal_path": str(causal_path),
            "output_dir": str(sim_dir)
        }

        # Save the manifest to a file
        manifest_path = sim_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Calculate the manifest hash
        with open(manifest_path, 'rb') as f:
            manifest_hash = hashlib.sha256(f.read()).hexdigest()

        # Run the simulation using the code interpreter
        report_progress("Running simulation in sandbox environment", 50)
        
        from arc_memory.simulate.code_interpreter import run_simulation
        
        simulation_results = run_simulation(
            manifest_path=str(manifest_path),
            duration_seconds=min(timeout, 300),  # Cap at 5 minutes for now
            metrics_interval=30,  # Collect metrics every 30 seconds
            progress_callback=lambda msg, pct: report_progress(msg, 50 + int(pct * 0.25)),  # Map to 50-75% of overall progress
            verbose=verbose  # Pass the verbose flag
        )

        # Parse the agent result
        try:
            simulation_results = json.loads(simulation_results)
        except json.JSONDecodeError:
            # Try to extract JSON from the output
            import re
            json_match = re.search(r'```json\n(.*?)\n```', simulation_results, re.DOTALL)
            if json_match:
                simulation_results = json.loads(json_match.group(1))
            else:
                raise ValueError("Agent output does not contain valid JSON")

        # Process the metrics
        report_progress("Processing simulation metrics", 75)

        # Import here to avoid circular imports
        from arc_memory.simulate.analysis import process_metrics, calculate_risk_score, identify_risk_factors

        processed_metrics = process_metrics(simulation_results, scenario, severity)

        # Calculate the risk score
        risk_score = calculate_risk_score(processed_metrics, scenario, severity, affected_services)

        # Identify risk factors
        risk_factors = identify_risk_factors(processed_metrics, scenario, severity, risk_score)

        # Generate the explanation
        report_progress("Generating explanation of simulation results", 85)

        # Import here to avoid circular imports
        from arc_memory.simulate.explanation_utils import generate_llm_explanation

        explanation = generate_llm_explanation(
            scenario=scenario,
            severity=severity,
            affected_services=affected_services,
            processed_metrics=processed_metrics,
            risk_score=risk_score,
            risk_factors=risk_factors,
            simulation_results=simulation_results,
            diff_data=diff_data,
            causal_graph=causal_graph,
            use_memory=use_memory,
            db_path=db_path
        )

        # Generate the attestation
        report_progress("Generating attestation for simulation results", 90)

        # Import here to avoid circular imports
        from arc_memory.simulate.attestation import generate_attestation

        # Calculate the diff hash
        diff_hash = hashlib.sha256(json.dumps(diff_data, sort_keys=True).encode()).hexdigest()

        # Get the target commit
        commit_target = rev_range.split("..")[-1] if ".." in rev_range else rev_range

        attestation = generate_attestation(
            rev_range=rev_range,
            scenario=scenario,
            severity=severity,
            risk_score=risk_score,
            affected_services=affected_services,
            metrics=processed_metrics,
            explanation=explanation,
            manifest_hash=manifest_hash,
            commit_target=commit_target,
            diff_hash=diff_hash
        )

        # Store in memory if requested
        if use_memory:
            report_progress("Storing simulation results in memory", 95)

            # Import here to avoid circular imports
            from arc_memory.simulate.memory import store_simulation_in_memory

            memory_node = store_simulation_in_memory(
                rev_range=rev_range,
                scenario=scenario,
                severity=severity,
                risk_score=risk_score,
                affected_services=affected_services,
                metrics=processed_metrics,
                explanation=explanation,
                attestation=attestation,
                diff_data=diff_data,
                db_path=db_path
            )

            # Enhance the explanation with historical context if memory node was created
            if memory_node:
                report_progress("Enhancing explanation with historical context", 97)

                # Import here to avoid circular imports
                from arc_memory.simulate.memory import enhance_explanation

                enhanced_explanation = enhance_explanation(
                    explanation=explanation,
                    affected_services=affected_services,
                    scenario=scenario,
                    severity=severity,
                    risk_score=risk_score,
                    db_path=db_path
                )

                # Update the explanation if it was enhanced
                if enhanced_explanation != explanation:
                    explanation = enhanced_explanation
                    logger.info("Enhanced explanation with historical context")
        else:
            memory_node = None

        # Prepare the final results
        results = {
            "status": "completed",
            "rev_range": rev_range,
            "scenario": scenario,
            "severity": severity,
            "affected_services": affected_services,
            "metrics": processed_metrics,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "explanation": explanation,
            "attestation": attestation,
            "memory_node": memory_node.id if memory_node else None,
            "timestamp": int(time.time())
        }

        # Update progress
        report_progress("Successfully completed simulation", 100)

        logger.info("Successfully completed simulation")
        return results
    except Exception as e:
        logger.error(f"Error running simulation workflow: {e}")

        # Update progress
        report_progress(f"Error running simulation workflow: {str(e)[:50]}...", 100)

        # Return error results
        return {
            "status": "failed",
            "error": str(e),
            "rev_range": rev_range,
            "scenario": scenario,
            "severity": severity,
            "timestamp": int(time.time())
        }
