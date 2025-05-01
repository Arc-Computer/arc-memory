"""Tests for the attestation module."""

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from arc_memory.attestation.write_attest import (
    generate_attestation_id,
    calculate_content_hash,
    sign_attestation,
    create_attestation,
    save_attestation,
    verify_attestation,
    generate_and_save_attestation
)


class TestWriteAttest:
    """Tests for the attestation module."""

    def test_generate_attestation_id(self):
        """Test generating attestation ID."""
        # Test with basic rev_range
        rev_range = "HEAD~1..HEAD"
        sim_id = generate_attestation_id(rev_range)
        assert sim_id == "sim_HEAD~1_HEAD"
        
        # Test with timestamp
        rev_range = "HEAD~1..HEAD"
        timestamp = "2023-01-01T12:34:56Z"
        sim_id = generate_attestation_id(rev_range, timestamp)
        assert sim_id == "sim_HEAD~1_HEAD_2023-01-01"
        
        # Test with complex rev_range
        rev_range = "feature/branch..main"
        sim_id = generate_attestation_id(rev_range)
        assert sim_id == "sim_feature_branch_main"

    def test_calculate_content_hash(self):
        """Test calculating content hash."""
        # Test with simple content
        content = {"key": "value"}
        hash_value = calculate_content_hash(content)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hash is 64 hex chars
        
        # Test with more complex content
        content = {
            "key1": "value1",
            "key2": {
                "nested": "value2"
            },
            "key3": [1, 2, 3]
        }
        hash_value = calculate_content_hash(content)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_sign_attestation(self):
        """Test signing attestation."""
        # Test with simple attestation
        attestation = {
            "sim_id": "sim_test",
            "key": "value"
        }
        
        # Mock the environment variable
        with mock.patch.dict(os.environ, {"ARC_SIGNING_KEY": "test_key"}):
            signed = sign_attestation(attestation)
        
        assert "signature" in signed
        assert "algorithm" in signed["signature"]
        assert "value" in signed["signature"]
        assert "timestamp" in signed["signature"]
        assert signed["signature"]["algorithm"] == "hmac-sha256"
        assert len(signed["signature"]["value"]) == 64  # SHA-256 hash is 64 hex chars

    def test_create_attestation(self):
        """Test creating attestation."""
        # Test with required parameters
        rev_range = "HEAD~1..HEAD"
        scenario = "network_latency"
        severity = 50
        affected_services = ["service1", "service2"]
        metrics = {"latency_ms": 500, "error_rate": 0.05}
        risk_score = 35
        explanation = "Test explanation"
        manifest_hash = "abcdef1234567890"
        commit_target = "abcdef1234567890"
        timestamp = "2023-01-01T12:34:56Z"
        diff_hash = "abcdef1234567890"
        
        # Mock the environment variable
        with mock.patch.dict(os.environ, {"ARC_SIGNING_KEY": "test_key"}):
            attestation = create_attestation(
                rev_range=rev_range,
                scenario=scenario,
                severity=severity,
                affected_services=affected_services,
                metrics=metrics,
                risk_score=risk_score,
                explanation=explanation,
                manifest_hash=manifest_hash,
                commit_target=commit_target,
                timestamp=timestamp,
                diff_hash=diff_hash
            )
        
        assert "sim_id" in attestation
        assert "version" in attestation
        assert "rev_range" in attestation
        assert "scenario" in attestation
        assert "severity" in attestation
        assert "affected_services" in attestation
        assert "metrics" in attestation
        assert "risk_score" in attestation
        assert "explanation" in attestation
        assert "manifest_hash" in attestation
        assert "commit_target" in attestation
        assert "timestamp" in attestation
        assert "diff_hash" in attestation
        assert "signature" in attestation
        
        # Test with simulation results
        simulation_results = {"key": "value"}
        
        with mock.patch.dict(os.environ, {"ARC_SIGNING_KEY": "test_key"}):
            attestation = create_attestation(
                rev_range=rev_range,
                scenario=scenario,
                severity=severity,
                affected_services=affected_services,
                metrics=metrics,
                risk_score=risk_score,
                explanation=explanation,
                manifest_hash=manifest_hash,
                commit_target=commit_target,
                timestamp=timestamp,
                diff_hash=diff_hash,
                simulation_results=simulation_results
            )
        
        assert "simulation_results_hash" in attestation

    def test_save_attestation(self):
        """Test saving attestation."""
        # Create a simple attestation
        attestation = {
            "sim_id": "sim_test",
            "key": "value"
        }
        
        # Test with explicit output path
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "attestation.json"
            saved_path = save_attestation(attestation, output_path)
            
            assert saved_path == output_path
            assert output_path.exists()
            
            # Check the content
            with open(output_path, 'r') as f:
                saved_attestation = json.load(f)
            
            assert saved_attestation == attestation
        
        # Test with default output path
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock ensure_arc_dir to return the temp directory
            with mock.patch("arc_memory.attestation.write_attest.ensure_arc_dir") as mock_ensure_arc_dir:
                mock_ensure_arc_dir.return_value = Path(temp_dir)
                
                saved_path = save_attestation(attestation)
                
                expected_path = Path(temp_dir) / ".attest" / "sim_test.json"
                assert saved_path == expected_path
                assert expected_path.exists()
                
                # Check the content
                with open(expected_path, 'r') as f:
                    saved_attestation = json.load(f)
                
                assert saved_attestation == attestation

    def test_verify_attestation(self):
        """Test verifying attestation."""
        # Create a signed attestation
        attestation = {
            "sim_id": "sim_test",
            "key": "value"
        }
        
        # Mock the environment variable
        with mock.patch.dict(os.environ, {"ARC_SIGNING_KEY": "test_key"}):
            signed = sign_attestation(attestation)
            
            # Test with valid signature
            assert verify_attestation(signed)
            
            # Test with invalid signature
            invalid = signed.copy()
            invalid["signature"]["value"] = "invalid"
            assert not verify_attestation(invalid)
            
            # Test with missing signature
            missing = signed.copy()
            del missing["signature"]
            assert not verify_attestation(missing)

    def test_generate_and_save_attestation(self):
        """Test generating and saving attestation."""
        # Test with required parameters
        rev_range = "HEAD~1..HEAD"
        scenario = "network_latency"
        severity = 50
        affected_services = ["service1", "service2"]
        metrics = {"latency_ms": 500, "error_rate": 0.05}
        risk_score = 35
        explanation = "Test explanation"
        manifest_hash = "abcdef1234567890"
        commit_target = "abcdef1234567890"
        timestamp = "2023-01-01T12:34:56Z"
        diff_hash = "abcdef1234567890"
        
        # Mock the environment variable and ensure_arc_dir
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"ARC_SIGNING_KEY": "test_key"}):
                with mock.patch("arc_memory.attestation.write_attest.ensure_arc_dir") as mock_ensure_arc_dir:
                    mock_ensure_arc_dir.return_value = Path(temp_dir)
                    
                    attestation = generate_and_save_attestation(
                        rev_range=rev_range,
                        scenario=scenario,
                        severity=severity,
                        affected_services=affected_services,
                        metrics=metrics,
                        risk_score=risk_score,
                        explanation=explanation,
                        manifest_hash=manifest_hash,
                        commit_target=commit_target,
                        timestamp=timestamp,
                        diff_hash=diff_hash
                    )
                    
                    assert "sim_id" in attestation
                    assert "signature" in attestation
                    
                    # Check that the file was saved
                    expected_path = Path(temp_dir) / ".attest" / f"{attestation['sim_id']}.json"
                    assert expected_path.exists()
                    
                    # Check with explicit output path
                    output_path = Path(temp_dir) / "attestation.json"
                    attestation = generate_and_save_attestation(
                        rev_range=rev_range,
                        scenario=scenario,
                        severity=severity,
                        affected_services=affected_services,
                        metrics=metrics,
                        risk_score=risk_score,
                        explanation=explanation,
                        manifest_hash=manifest_hash,
                        commit_target=commit_target,
                        timestamp=timestamp,
                        diff_hash=diff_hash,
                        output_path=output_path
                    )
                    
                    assert "sim_id" in attestation
                    assert "signature" in attestation
                    assert output_path.exists()
