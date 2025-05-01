"""Results analysis and explanation generation for Arc Memory simulations.

This module provides functionality for analyzing simulation results,
calculating risk scores, and generating human-readable explanations.
"""

import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def process_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Process and normalize raw metrics from simulation.

    Args:
        metrics: Raw metrics from simulation

    Returns:
        Processed metrics with derived values
    """
    processed_metrics = metrics.copy()

    # Calculate derived metrics if we have the necessary data
    if "latency_ms" in metrics:
        # Normalize latency to a 0-1 scale (assuming max reasonable latency is 2000ms)
        latency = metrics["latency_ms"]
        processed_metrics["normalized_latency"] = min(1.0, latency / 2000.0)

    if "error_rate" in metrics:
        # Error rate is already a 0-1 scale
        error_rate = metrics["error_rate"]
        processed_metrics["normalized_error_rate"] = error_rate

    # Process resource usage metrics if available
    if "cpu_usage" in metrics and isinstance(metrics["cpu_usage"], dict):
        # Calculate average CPU usage across services
        cpu_values = list(metrics["cpu_usage"].values())
        if cpu_values:
            processed_metrics["avg_cpu_usage"] = sum(cpu_values) / len(cpu_values)
            processed_metrics["max_cpu_usage"] = max(cpu_values)
            # Normalize to 0-1 scale (assuming 1.0 is 100% of a CPU core)
            processed_metrics["normalized_cpu_usage"] = min(1.0, processed_metrics["max_cpu_usage"])

    if "memory_usage" in metrics and isinstance(metrics["memory_usage"], dict):
        # Calculate average memory usage across services (in MB)
        memory_values = list(metrics["memory_usage"].values())
        if memory_values:
            processed_metrics["avg_memory_usage"] = sum(memory_values) / len(memory_values)
            processed_metrics["max_memory_usage"] = max(memory_values)
            # Normalize to 0-1 scale (assuming 1024MB is a reasonable threshold)
            processed_metrics["normalized_memory_usage"] = min(1.0, processed_metrics["max_memory_usage"] / 1024.0)

    return processed_metrics


def calculate_risk_score(
    processed_metrics: Dict[str, Any],
    severity: int,
    affected_services: List[str]
) -> Tuple[int, Dict[str, float]]:
    """Calculate a risk score based on processed metrics and simulation parameters.

    Args:
        processed_metrics: Processed metrics from simulation
        severity: The severity level of the simulation (0-100)
        affected_services: List of services affected by the changes

    Returns:
        A tuple of (risk_score, risk_factors) where risk_score is an integer 0-100
        and risk_factors is a dictionary of contributing factors and their weights
    """
    # Initialize risk factors
    risk_factors = {
        "severity": severity / 100.0,  # Normalize to 0-1
        "service_count": min(1.0, len(affected_services) / 10.0),  # Normalize to 0-1 (cap at 10 services)
    }

    # Add normalized metrics to risk factors
    for key, value in processed_metrics.items():
        if key.startswith("normalized_") and isinstance(value, (int, float)):
            risk_factors[key] = value

    # Define weights for each factor
    weights = {
        "severity": 0.3,
        "service_count": 0.2,
        "normalized_latency": 0.2,
        "normalized_error_rate": 0.2,
        "normalized_cpu_usage": 0.05,
        "normalized_memory_usage": 0.05
    }

    # Calculate weighted risk score
    weighted_sum = 0.0
    total_weight = 0.0

    for factor, value in risk_factors.items():
        if factor in weights:
            weighted_sum += value * weights[factor]
            total_weight += weights[factor]

    # Normalize by actual weights used
    if total_weight > 0:
        normalized_score = weighted_sum / total_weight
    else:
        # Fallback to severity-based score if no weights were applied
        normalized_score = severity / 100.0

    # Convert to 0-100 scale
    risk_score = int(normalized_score * 100)

    return risk_score, risk_factors


def generate_explanation(
    scenario: str,
    severity: int,
    affected_services: List[str],
    processed_metrics: Dict[str, Any],
    risk_score: int,
    risk_factors: Dict[str, float],
    simulation_results: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a human-readable explanation of simulation results.

    Args:
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        affected_services: List of services affected by the changes
        processed_metrics: Processed metrics from simulation
        risk_score: Calculated risk score (0-100)
        risk_factors: Dictionary of risk factors and their values
        simulation_results: Optional raw simulation results

    Returns:
        A human-readable explanation of the simulation results
    """
    # Format the scenario name for display
    scenario_display = scenario.replace("_", " ").title()

    # Start with a summary
    explanation = [
        f"# Simulation Results Summary",
        f"",
        f"A {scenario_display} simulation was conducted with severity level {severity}/100, ",
        f"affecting {len(affected_services)} service(s)."
    ]

    # Add risk assessment
    if risk_score < 25:
        risk_level = "Low"
        recommendation = "This change appears safe to merge."
    elif risk_score < 50:
        risk_level = "Moderate"
        recommendation = "Review the metrics before merging this change."
    elif risk_score < 75:
        risk_level = "High"
        recommendation = "Consider revising this change to reduce its impact."
    else:
        risk_level = "Critical"
        recommendation = "This change requires significant revision before merging."

    explanation.extend([
        f"",
        f"## Risk Assessment",
        f"",
        f"Risk Score: {risk_score}/100 ({risk_level} Risk)",
        f"",
        f"{recommendation}"
    ])

    # Add affected services
    explanation.extend([
        f"",
        f"## Affected Services",
        f""
    ])

    for service in affected_services:
        explanation.append(f"- {service}")

    # Add key metrics
    explanation.extend([
        f"",
        f"## Key Metrics",
        f""
    ])

    # Add latency and error rate if available
    if "latency_ms" in processed_metrics:
        explanation.append(f"- Latency: {processed_metrics['latency_ms']} ms")
    if "error_rate" in processed_metrics:
        explanation.append(f"- Error Rate: {processed_metrics['error_rate'] * 100:.2f}%")

    # Add resource usage if available
    if "avg_cpu_usage" in processed_metrics:
        explanation.append(f"- Avg CPU Usage: {processed_metrics['avg_cpu_usage'] * 100:.2f}%")
    if "max_cpu_usage" in processed_metrics:
        explanation.append(f"- Max CPU Usage: {processed_metrics['max_cpu_usage'] * 100:.2f}%")
    if "avg_memory_usage" in processed_metrics:
        explanation.append(f"- Avg Memory Usage: {processed_metrics['avg_memory_usage']:.2f} MB")
    if "max_memory_usage" in processed_metrics:
        explanation.append(f"- Max Memory Usage: {processed_metrics['max_memory_usage']:.2f} MB")

    # Add contributing factors to risk score
    explanation.extend([
        f"",
        f"## Contributing Risk Factors",
        f""
    ])

    # Sort risk factors by their contribution (value)
    sorted_factors = sorted(
        [(k, v) for k, v in risk_factors.items()],
        key=lambda x: x[1],
        reverse=True
    )

    for factor, value in sorted_factors:
        # Format the factor name for display
        factor_display = factor.replace("normalized_", "").replace("_", " ").title()
        explanation.append(f"- {factor_display}: {value * 100:.2f}%")

    # Join all lines with newlines
    return "\n".join(explanation)


def analyze_simulation_results(
    scenario: str,
    severity: int,
    affected_services: List[str],
    metrics: Dict[str, Any],
    simulation_results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze simulation results and generate risk assessment.

    Args:
        scenario: The fault scenario that was simulated
        severity: The severity level of the simulation (0-100)
        affected_services: List of services affected by the changes
        metrics: Raw metrics from simulation
        simulation_results: Optional raw simulation results

    Returns:
        A dictionary containing processed metrics, risk score, and explanation
    """
    logger.info("Analyzing simulation results")

    # Process metrics
    processed_metrics = process_metrics(metrics)

    # Calculate risk score
    risk_score, risk_factors = calculate_risk_score(
        processed_metrics,
        severity,
        affected_services
    )

    # Generate explanation
    explanation = generate_explanation(
        scenario,
        severity,
        affected_services,
        processed_metrics,
        risk_score,
        risk_factors,
        simulation_results
    )

    return {
        "processed_metrics": processed_metrics,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "explanation": explanation
    }
