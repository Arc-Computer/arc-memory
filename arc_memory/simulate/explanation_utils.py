"""LLM-based explanation generation utilities for Arc Memory simulation.

This module provides utilities for generating human-readable explanations of
simulation results using LLMs.
"""

import os
import json
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.utils.progress import create_progress_reporter
# Define a simple explanation generator function
def generate_explanation_from_module(
    scenario: str,
    severity: int,
    affected_services: List[str],
    processed_metrics: Dict[str, Any],
    risk_score: int,
    risk_factors: Dict[str, Any],
    simulation_results: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a simple explanation without using an LLM.

    Args:
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        affected_services: List of affected services
        processed_metrics: Processed metrics
        risk_score: Calculated risk score
        risk_factors: Risk factors
        simulation_results: Raw simulation results (optional)

    Returns:
        A human-readable explanation
    """
    # Format the scenario name for display
    scenario_display = scenario.replace("_", " ").title()

    # Create the explanation
    explanation = f"""# Simulation Results

## Overview
- **Scenario**: {scenario_display}
- **Severity**: {severity}/100
- **Risk Score**: {risk_score}/100
- **Affected Services**: {', '.join(affected_services)}

## Risk Assessment
The simulation tested the impact of a {scenario_display} scenario with severity {severity} on {len(affected_services)} services.
"""

    # Add metrics
    explanation += "\n## Metrics\n"
    for key, value in processed_metrics.items():
        if not isinstance(value, dict) and not isinstance(value, list):
            explanation += f"- **{key}**: {value}\n"

    # Add risk factors
    explanation += "\n## Risk Factors\n"
    for factor, value in risk_factors.items():
        factor_display = factor.replace("_", " ").title()
        explanation += f"- **{factor_display}**: {value}\n"

    # Add recommendations
    explanation += "\n## Recommendations\n"

    if risk_score > 75:
        explanation += "- 🔴 **High Risk**: This change has a high risk of causing issues in production. Consider breaking it down into smaller, less risky changes.\n"
    elif risk_score > 50:
        explanation += "- 🟠 **Medium Risk**: This change has a moderate risk. Ensure thorough testing before deployment.\n"
    else:
        explanation += "- 🟢 **Low Risk**: This change has a low risk. Standard testing procedures should be sufficient.\n"

    return explanation

logger = get_logger(__name__)

# Check if OpenAI is available
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def generate_llm_explanation(
    scenario: str,
    severity: int,
    affected_services: List[str],
    processed_metrics: Dict[str, Any],
    risk_score: int,
    risk_factors: Dict[str, Any],
    simulation_results: Optional[Dict[str, Any]] = None,
    diff_data: Optional[Dict[str, Any]] = None,
    causal_graph: Optional[Dict[str, Any]] = None,
    llm_provider: str = "openai",
    model_name: str = "gpt-4o",
    progress_callback: Optional[Callable[[str, int], None]] = None,
    use_memory: bool = False,
    db_path: Optional[str] = None
) -> str:
    """Generate a human-readable explanation of the simulation results using an LLM.

    Args:
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        affected_services: List of affected service names
        processed_metrics: Processed metrics from the simulation
        risk_score: Calculated risk score
        risk_factors: Dictionary containing risk factors
        simulation_results: Raw simulation results (optional)
        diff_data: Dictionary containing the diff data (optional)
        causal_graph: Dictionary containing the causal graph (optional)
        llm_provider: LLM provider (default: "openai")
        model_name: Model name (default: "gpt-4o")
        progress_callback: Callback function to update progress (optional)

    Returns:
        Human-readable explanation

    Raises:
        RuntimeError: If the explanation cannot be generated
    """
    # Create a progress reporter
    report_progress = create_progress_reporter(progress_callback)

    # Update progress
    report_progress("Generating explanation of simulation results", 75)

    logger.info("Generating explanation")

    try:
        # Check if we can use OpenAI
        if llm_provider == "openai" and not HAS_OPENAI:
            error_msg = "OpenAI package is not available. Please install it with 'pip install openai'."
            logger.error(error_msg)

            # Update progress
            report_progress(error_msg, 100)

            # Fall back to built-in explanation generator
            return generate_explanation_from_module(
                scenario=scenario,
                severity=severity,
                affected_services=affected_services,
                processed_metrics=processed_metrics,
                risk_score=risk_score,
                risk_factors=risk_factors,
                simulation_results=simulation_results
            )

        # Get the OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OpenAI API key not found in environment variables."
            logger.error(error_msg)

            # Update progress
            report_progress(error_msg, 100)

            # Fall back to built-in explanation generator
            return generate_explanation_from_module(
                scenario=scenario,
                severity=severity,
                affected_services=affected_services,
                processed_metrics=processed_metrics,
                risk_score=risk_score,
                risk_factors=risk_factors,
                simulation_results=simulation_results
            )

        # Initialize the OpenAI client
        client = openai.OpenAI(api_key=api_key)

        # Prepare the prompt
        prompt = f"""
You are an expert system reliability engineer analyzing the results of a fault injection simulation.

Scenario: {scenario}
Severity: {severity}/100
Affected Services: {', '.join(affected_services) if affected_services else 'None'}
Risk Score: {risk_score}/100

Metrics:
{json.dumps(processed_metrics, indent=2)}

Risk Factors:
{json.dumps(risk_factors, indent=2)}

Please provide a detailed explanation of the simulation results, including:
1. A summary of the changes and their impact
2. An analysis of the risk factors and their significance
3. Recommendations for mitigating the identified risks
4. Any additional insights or concerns

Your explanation should be technical but accessible to developers who are not reliability experts.
"""

        # Add diff data if available
        if diff_data:
            # Limit the diff data to avoid token limits
            files_changed = len(diff_data.get("files", []))
            prompt += f"\nFiles Changed: {files_changed}\n"

            # Add a sample of the changed files
            sample_files = diff_data.get("files", [])[:5]
            for file in sample_files:
                prompt += f"- {file.get('path', 'Unknown')}\n"

        # Generate the explanation
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert system reliability engineer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )

        # Extract the explanation
        explanation = response.choices[0].message.content.strip()

        # Update progress
        report_progress("Successfully generated explanation", 80)

        # Enhance the explanation with historical context if requested
        if use_memory and db_path:
            try:
                # Import here to avoid circular imports
                from arc_memory.simulate.memory import enhance_explanation

                report_progress("Enhancing explanation with historical context", 85)

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
            except Exception as e:
                logger.error(f"Error enhancing explanation with memory: {e}")
                # Continue with the original explanation

        logger.info("Successfully generated explanation")
        return explanation
    except Exception as e:
        logger.error(f"Error generating explanation: {e}")

        # Update progress
        report_progress(f"Error generating explanation: {str(e)[:50]}...", 100)

        # Fall back to built-in explanation generator
        return generate_explanation_from_module(
            scenario=scenario,
            severity=severity,
            affected_services=affected_services,
            processed_metrics=processed_metrics,
            risk_score=risk_score,
            risk_factors=risk_factors,
            simulation_results=simulation_results
        )


def enhance_explanation_with_memory(
    explanation: str,
    relevant_simulations: List[Dict[str, Any]],
    llm_provider: str = "openai",
    model_name: str = "gpt-4o"
) -> str:
    """Enhance the explanation with memory from relevant simulations.

    Args:
        explanation: Original explanation
        relevant_simulations: List of relevant simulations from memory
        llm_provider: LLM provider (default: "openai")
        model_name: Model name (default: "gpt-4o")

    Returns:
        Enhanced explanation
    """
    if not relevant_simulations:
        return explanation

    logger.info(f"Enhancing explanation with {len(relevant_simulations)} relevant simulations")

    try:
        # Check if we can use OpenAI
        if llm_provider == "openai" and not HAS_OPENAI:
            logger.error("OpenAI package is not available. Cannot enhance explanation with memory.")
            return explanation

        # Get the OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found in environment variables. Cannot enhance explanation with memory.")
            return explanation

        # Initialize the OpenAI client
        client = openai.OpenAI(api_key=api_key)

        # Prepare the prompt
        prompt = f"""
You are enhancing an explanation of simulation results with historical context from previous simulations.

Original Explanation:
{explanation}

Relevant Historical Simulations:
"""

        # Add relevant simulations
        for i, sim in enumerate(relevant_simulations[:3]):  # Limit to 3 simulations
            prompt += f"\nSimulation {i+1}:\n"
            prompt += f"- Date: {sim.get('timestamp', 'Unknown')}\n"
            prompt += f"- Risk Score: {sim.get('risk_score', 0)}/100\n"
            prompt += f"- Affected Services: {', '.join(sim.get('affected_services', []))}\n"

            # Add a snippet of the explanation
            sim_explanation = sim.get("explanation", "")
            if sim_explanation:
                # Limit the explanation to 200 characters
                snippet = sim_explanation[:200] + "..." if len(sim_explanation) > 200 else sim_explanation
                prompt += f"- Explanation Snippet: {snippet}\n"

        prompt += """
Please enhance the original explanation with insights from these historical simulations. Focus on:
1. Patterns or trends across simulations
2. Services that are frequently affected
3. How the current simulation compares to previous ones
4. Any additional context that would help understand the current results

Maintain the original structure and technical accuracy while adding this historical context.
"""

        # Generate the enhanced explanation
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert system reliability engineer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        # Extract the enhanced explanation
        enhanced_explanation = response.choices[0].message.content.strip()

        logger.info("Successfully enhanced explanation with memory")
        return enhanced_explanation
    except Exception as e:
        logger.error(f"Error enhancing explanation with memory: {e}")
        return explanation
