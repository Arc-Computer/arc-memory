"""Tests for the explanation module."""

import pytest
from arc_memory.simulate.explanation import (
    process_metrics,
    calculate_risk_score,
    generate_explanation,
    analyze_simulation_results
)


class TestExplanation:
    """Tests for the explanation module."""

    def test_process_metrics(self):
        """Test processing metrics."""
        # Test with basic metrics
        metrics = {
            "latency_ms": 500,
            "error_rate": 0.05
        }
        processed = process_metrics(metrics)

        assert "normalized_latency" in processed
        assert "normalized_error_rate" in processed
        assert processed["normalized_latency"] == 0.25  # 500/2000
        assert processed["normalized_error_rate"] == 0.05

        # Test with resource usage metrics
        metrics = {
            "latency_ms": 500,
            "error_rate": 0.05,
            "cpu_usage": {
                "service1": 0.5,
                "service2": 0.7
            },
            "memory_usage": {
                "service1": 200,
                "service2": 300
            }
        }
        processed = process_metrics(metrics)

        assert "avg_cpu_usage" in processed
        assert "max_cpu_usage" in processed
        assert "normalized_cpu_usage" in processed
        assert processed["avg_cpu_usage"] == 0.6
        assert processed["max_cpu_usage"] == 0.7
        assert processed["normalized_cpu_usage"] == 0.7

        assert "avg_memory_usage" in processed
        assert "max_memory_usage" in processed
        assert "normalized_memory_usage" in processed
        assert processed["avg_memory_usage"] == 250
        assert processed["max_memory_usage"] == 300
        assert processed["normalized_memory_usage"] == pytest.approx(300/1024)

    def test_calculate_risk_score(self):
        """Test calculating risk score."""
        # Test with basic metrics
        processed_metrics = {
            "normalized_latency": 0.25,
            "normalized_error_rate": 0.05
        }
        severity = 50
        affected_services = ["service1", "service2"]

        risk_score, risk_factors = calculate_risk_score(
            processed_metrics,
            severity,
            affected_services
        )

        assert isinstance(risk_score, int)
        assert 0 <= risk_score <= 100
        assert "severity" in risk_factors
        assert "service_count" in risk_factors
        assert "normalized_latency" in risk_factors
        assert "normalized_error_rate" in risk_factors

        # Test with more metrics
        processed_metrics = {
            "normalized_latency": 0.25,
            "normalized_error_rate": 0.05,
            "normalized_cpu_usage": 0.7,
            "normalized_memory_usage": 0.3
        }

        risk_score, risk_factors = calculate_risk_score(
            processed_metrics,
            severity,
            affected_services
        )

        assert isinstance(risk_score, int)
        assert 0 <= risk_score <= 100
        assert "normalized_cpu_usage" in risk_factors
        assert "normalized_memory_usage" in risk_factors

    def test_generate_explanation(self):
        """Test generating explanation."""
        # Test with basic inputs
        scenario = "network_latency"
        severity = 50
        affected_services = ["service1", "service2"]
        processed_metrics = {
            "latency_ms": 500,
            "error_rate": 0.05,
            "normalized_latency": 0.25,
            "normalized_error_rate": 0.05
        }
        risk_score = 35
        risk_factors = {
            "severity": 0.5,
            "service_count": 0.2,
            "normalized_latency": 0.25,
            "normalized_error_rate": 0.05
        }

        explanation = generate_explanation(
            scenario,
            severity,
            affected_services,
            processed_metrics,
            risk_score,
            risk_factors
        )

        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Simulation Results Summary" in explanation
        assert "Risk Assessment" in explanation
        assert "Risk Score: 35/100" in explanation
        assert "Affected Services" in explanation
        assert "service1" in explanation
        assert "service2" in explanation
        assert "Key Metrics" in explanation
        assert "Contributing Risk Factors" in explanation

    def test_analyze_simulation_results(self):
        """Test analyzing simulation results."""
        # Test with basic inputs
        scenario = "network_latency"
        severity = 50
        affected_services = ["service1", "service2"]
        metrics = {
            "latency_ms": 500,
            "error_rate": 0.05
        }

        results = analyze_simulation_results(
            scenario,
            severity,
            affected_services,
            metrics
        )

        assert "processed_metrics" in results
        assert "risk_score" in results
        assert "risk_factors" in results
        assert "explanation" in results
        assert isinstance(results["risk_score"], int)
        assert 0 <= results["risk_score"] <= 100
        assert isinstance(results["explanation"], str)
        assert len(results["explanation"]) > 0
