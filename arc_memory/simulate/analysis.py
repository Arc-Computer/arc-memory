"""Metrics analysis and risk scoring module for Arc Memory simulation.

This module provides functions for analyzing metrics from simulations and
calculating risk scores.
"""

import math
from typing import Dict, List, Any, Optional, Callable

from arc_memory.logging_conf import get_logger
from arc_memory.simulate.utils.progress import create_progress_reporter

logger = get_logger(__name__)


def process_metrics(
    metrics: Dict[str, Any],
    scenario: str,
    severity: int,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Dict[str, Any]:
    """Process raw metrics from the simulation.
    
    Args:
        metrics: Raw metrics from the simulation
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        progress_callback: Callback function to update progress (optional)
        
    Returns:
        Dictionary containing processed metrics
        
    Raises:
        ValueError: If the metrics are invalid
    """
    # Create a progress reporter
    report_progress = create_progress_reporter(progress_callback)
    
    # Update progress
    report_progress("Processing simulation metrics", 75)
    
    logger.info("Processing simulation metrics")

    try:
        # Check if we have metrics
        if not metrics:
            error_msg = "No metrics available for processing"
            logger.error(error_msg)
            
            # Update progress
            report_progress(error_msg, 100)
            
            raise ValueError(error_msg)
        
        # Extract initial and final metrics
        initial_metrics = metrics.get("initial_metrics", {})
        final_metrics = metrics.get("final_metrics", {})
        
        # Calculate deltas
        processed_metrics = {
            "latency_ms": final_metrics.get("latency_ms", 0),
            "error_rate": final_metrics.get("error_rate", 0),
            "throughput": final_metrics.get("throughput", 0),
            "cpu_usage": final_metrics.get("cpu_usage", 0),
            "memory_usage": final_metrics.get("memory_usage", 0),
            "deltas": {}
        }
        
        # Calculate deltas for each metric
        for key in final_metrics:
            if key in initial_metrics:
                initial_value = initial_metrics.get(key, 0)
                final_value = final_metrics.get(key, 0)
                
                # Skip non-numeric values
                if not isinstance(initial_value, (int, float)) or not isinstance(final_value, (int, float)):
                    continue
                
                processed_metrics["deltas"][key] = final_value - initial_value
        
        # Update progress
        report_progress("Successfully processed metrics", 80)
        
        logger.info("Successfully processed metrics")
        return processed_metrics
    except Exception as e:
        logger.error(f"Error processing metrics: {e}")
        
        # Update progress
        report_progress(f"Error processing metrics: {str(e)[:50]}...", 100)
        
        raise ValueError(f"Error processing metrics: {e}")


def calculate_risk_score(
    processed_metrics: Dict[str, Any],
    scenario: str,
    severity: int,
    affected_services: List[str],
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> int:
    """Calculate the risk score based on processed metrics.
    
    Args:
        processed_metrics: Processed metrics from the simulation
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        affected_services: List of affected service names
        progress_callback: Callback function to update progress (optional)
        
    Returns:
        Risk score (0-100)
    """
    # Create a progress reporter
    report_progress = create_progress_reporter(progress_callback)
    
    # Update progress
    report_progress("Calculating risk score", 85)
    
    logger.info("Calculating risk score")

    try:
        # Base risk is proportional to severity
        base_risk = severity * 0.5
        
        # Add risk based on metrics
        metrics_risk = 0
        
        # Latency risk (higher latency = higher risk)
        latency_ms = processed_metrics.get("latency_ms", 0)
        if latency_ms > 0:
            # Normalize latency to 0-25 range
            latency_risk = min(25, latency_ms / 20)
            metrics_risk += latency_risk
        
        # Error rate risk (higher error rate = higher risk)
        error_rate = processed_metrics.get("error_rate", 0)
        if error_rate > 0:
            # Normalize error rate to 0-25 range (1% error rate = 2.5 points)
            error_risk = min(25, error_rate * 250)
            metrics_risk += error_risk
        
        # Service count risk (more affected services = higher risk)
        service_count = len(affected_services)
        service_risk = min(25, service_count * 5)
        
        # Calculate total risk score
        risk_score = int(base_risk + metrics_risk + service_risk)
        
        # Ensure risk score is in 0-100 range
        risk_score = max(0, min(100, risk_score))
        
        # Update progress
        report_progress(f"Calculated risk score: {risk_score}", 90)
        
        logger.info(f"Calculated risk score: {risk_score}")
        return risk_score
    except Exception as e:
        logger.error(f"Error calculating risk score: {e}")
        
        # Update progress
        report_progress(f"Error calculating risk score: {str(e)[:50]}...", 100)
        
        # Return a default risk score
        return 50


def identify_risk_factors(
    processed_metrics: Dict[str, Any],
    scenario: str,
    severity: int,
    risk_score: int
) -> Dict[str, Any]:
    """Identify risk factors based on processed metrics.
    
    Args:
        processed_metrics: Processed metrics from the simulation
        scenario: Fault scenario ID
        severity: Severity level (0-100)
        risk_score: Calculated risk score
        
    Returns:
        Dictionary containing risk factors
    """
    logger.info("Identifying risk factors")

    try:
        risk_factors = {}
        
        # Latency risk factor
        latency_ms = processed_metrics.get("latency_ms", 0)
        if latency_ms > 100:
            risk_factors["high_latency"] = {
                "value": latency_ms,
                "threshold": 100,
                "impact": "high" if latency_ms > 500 else "medium"
            }
        
        # Error rate risk factor
        error_rate = processed_metrics.get("error_rate", 0)
        if error_rate > 0.01:  # 1% error rate
            risk_factors["high_error_rate"] = {
                "value": error_rate,
                "threshold": 0.01,
                "impact": "high" if error_rate > 0.05 else "medium"
            }
        
        # Throughput risk factor
        throughput = processed_metrics.get("throughput", 0)
        if throughput < 100:
            risk_factors["low_throughput"] = {
                "value": throughput,
                "threshold": 100,
                "impact": "medium"
            }
        
        # Resource usage risk factors
        cpu_usage = processed_metrics.get("cpu_usage", 0)
        if cpu_usage > 80:
            risk_factors["high_cpu_usage"] = {
                "value": cpu_usage,
                "threshold": 80,
                "impact": "medium"
            }
        
        memory_usage = processed_metrics.get("memory_usage", 0)
        if memory_usage > 80:
            risk_factors["high_memory_usage"] = {
                "value": memory_usage,
                "threshold": 80,
                "impact": "medium"
            }
        
        logger.info(f"Identified {len(risk_factors)} risk factors")
        return risk_factors
    except Exception as e:
        logger.error(f"Error identifying risk factors: {e}")
        return {}
