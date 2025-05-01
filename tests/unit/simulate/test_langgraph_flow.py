"""Tests for the LangGraph workflow."""

import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from arc_memory.simulate.langgraph_flow import (
    SimulationState,
    extract_diff,
    analyze_changes,
    build_causal_graph,
    generate_manifest,
    run_simulation,
    create_embeddings_from_diff,
    generate_explanation,
    generate_attestation,
    should_continue,
    create_workflow,
    run_sim,
    get_llm
)


class TestLangGraphFlow:
    """Tests for the LangGraph workflow."""

    def test_extract_diff_success(self):
        """Test extracting diff successfully."""
        # Setup
        state = {
            "rev_range": "HEAD~1..HEAD",
            "repo_path": os.getcwd(),
            "status": "in_progress"
        }

        # Mock the serialize_diff function
        with mock.patch("arc_memory.simulate.langgraph_flow.serialize_diff") as mock_serialize_diff:
            mock_serialize_diff.return_value = {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ],
                "end_commit": "abc123",
                "timestamp": "2023-01-01T00:00:00Z"
            }

            # Execute
            result = extract_diff(state)

            # Verify
            assert result["diff_data"] is not None
            assert len(result["diff_data"]["files"]) == 2
            assert result["status"] == "in_progress"
            mock_serialize_diff.assert_called_once_with("HEAD~1..HEAD", repo_path=os.getcwd())

    def test_extract_diff_failure(self):
        """Test extracting diff with failure."""
        # Setup
        state = {
            "rev_range": "HEAD~1..HEAD",
            "repo_path": os.getcwd(),
            "status": "in_progress"
        }

        # Mock the serialize_diff function
        with mock.patch("arc_memory.simulate.langgraph_flow.serialize_diff") as mock_serialize_diff:
            mock_serialize_diff.side_effect = Exception("Test error")

            # Execute
            result = extract_diff(state)

            # Verify
            assert result["error"] is not None
            assert "Test error" in result["error"]
            assert result["status"] == "failed"
            mock_serialize_diff.assert_called_once_with("HEAD~1..HEAD", repo_path=os.getcwd())

    def test_analyze_changes_success(self):
        """Test analyzing changes successfully."""
        # Setup
        state = {
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ]
            },
            "db_path": "/path/to/db",
            "status": "in_progress"
        }

        # Mock the analyze_diff function
        with mock.patch("arc_memory.simulate.langgraph_flow.analyze_diff") as mock_analyze_diff:
            mock_analyze_diff.return_value = ["service1", "service2"]

            # Execute
            result = analyze_changes(state)

            # Verify
            assert result["affected_services"] is not None
            assert len(result["affected_services"]) == 2
            assert "service1" in result["affected_services"]
            assert "service2" in result["affected_services"]
            assert result["status"] == "in_progress"
            mock_analyze_diff.assert_called_once_with(state["diff_data"], "/path/to/db")

    def test_analyze_changes_no_diff(self):
        """Test analyzing changes with no diff data."""
        # Setup
        state = {
            "db_path": "/path/to/db",
            "status": "in_progress"
        }

        # Execute
        result = analyze_changes(state)

        # Verify
        assert result["error"] is not None
        assert "No diff data" in result["error"]
        assert result["status"] == "failed"

    def test_build_causal_graph_success(self):
        """Test building causal graph successfully."""
        # Setup
        state = {
            "db_path": "/path/to/db",
            "status": "in_progress"
        }

        # Mock the derive_causal function
        with mock.patch("arc_memory.simulate.langgraph_flow.derive_causal") as mock_derive_causal:
            mock_derive_causal.return_value = {
                "nodes": ["service1", "service2"],
                "edges": [{"source": "service1", "target": "service2"}]
            }

            # Execute
            result = build_causal_graph(state)

            # Verify
            assert result["causal_graph"] is not None
            assert "nodes" in result["causal_graph"]
            assert "edges" in result["causal_graph"]
            assert result["status"] == "in_progress"
            mock_derive_causal.assert_called_once_with("/path/to/db")

    def test_build_causal_graph_failure(self):
        """Test building causal graph with failure."""
        # Setup
        state = {
            "db_path": "/path/to/db",
            "status": "in_progress"
        }

        # Mock the derive_causal function
        with mock.patch("arc_memory.simulate.langgraph_flow.derive_causal") as mock_derive_causal:
            mock_derive_causal.side_effect = Exception("Test error")

            # Execute
            result = build_causal_graph(state)

            # Verify
            assert result["error"] is not None
            assert "Test error" in result["error"]
            assert result["status"] == "failed"
            mock_derive_causal.assert_called_once_with("/path/to/db")

    def test_generate_manifest_success(self):
        """Test generating manifest successfully."""
        # Setup
        state = {
            "rev_range": "HEAD~1..HEAD",  # Add rev_range which is used for the hash
            "causal_graph": {
                "nodes": ["service1", "service2"],
                "edges": [{"source": "service1", "target": "service2"}]
            },
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ]
            },
            "affected_services": ["service1", "service2"],
            "scenario": "network_latency",
            "severity": 50,
            "status": "in_progress"
        }

        # Mock the generate_simulation_manifest function
        with mock.patch("arc_memory.simulate.langgraph_flow.generate_simulation_manifest") as mock_generate_manifest:
            mock_generate_manifest.return_value = {
                "kind": "NetworkChaos",
                "metadata": {
                    "name": "test-experiment",
                    "annotations": {
                        "arc-memory.io/manifest-hash": "abc123"
                    }
                }
            }

            # Mock ensure_arc_dir and Path.mkdir
            with mock.patch("arc_memory.simulate.langgraph_flow.ensure_arc_dir") as mock_ensure_arc_dir:
                mock_ensure_arc_dir.return_value = Path("/path/to/.arc")

                # Mock Path.mkdir to avoid directory creation error
                with mock.patch("pathlib.Path.mkdir") as mock_mkdir:
                    # Execute
                    result = generate_manifest(state)

                    # Verify
                    assert result["manifest"] is not None
                    assert result["manifest_path"] is not None
                    assert result["manifest"]["metadata"]["annotations"]["arc-memory.io/manifest-hash"] == "abc123"
                    assert result["status"] == "in_progress"
                    mock_generate_manifest.assert_called_once()
                    mock_ensure_arc_dir.assert_called_once()
                    mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_generate_manifest_missing_data(self):
        """Test generating manifest with missing data."""
        # Setup - missing causal graph
        state = {
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ]
            },
            "affected_services": ["service1", "service2"],
            "scenario": "network_latency",
            "severity": 50,
            "status": "in_progress"
        }

        # Execute
        result = generate_manifest(state)

        # Verify
        assert result["error"] is not None
        assert "No causal graph" in result["error"]
        assert result["status"] == "failed"

    def test_run_simulation_success(self):
        """Test running simulation successfully."""
        # Setup
        state = {
            "manifest_path": "/path/to/manifest.yaml",
            "scenario": "network_latency",
            "severity": 50,
            "timeout": 300,
            "status": "in_progress"
        }

        # Mock HAS_E2B and run_sandbox_simulation
        with mock.patch("arc_memory.simulate.langgraph_flow.HAS_E2B", True):
            with mock.patch("arc_memory.simulate.langgraph_flow.run_sandbox_simulation") as mock_run_simulation:
                mock_run_simulation.return_value = {
                    "experiment_name": "test-experiment",
                    "duration_seconds": 300,
                    "initial_metrics": {
                        "node_count": 1,
                        "pod_count": 5,
                        "service_count": 3
                    },
                    "final_metrics": {
                        "node_count": 1,
                        "pod_count": 5,
                        "service_count": 3,
                        "cpu_usage": {"service1": 0.5},
                        "memory_usage": {"service1": 100}
                    }
                }

                # Execute
                result = run_simulation(state)

                # Verify
                assert result["simulation_results"] is not None
                assert result["metrics"] is not None
                assert result["risk_score"] is not None
                assert "node_count" in result["metrics"]
                assert "cpu_usage" in result["metrics"]
                assert "memory_usage" in result["metrics"]
                assert result["status"] == "in_progress"
                mock_run_simulation.assert_called_once_with(
                    manifest_path="/path/to/manifest.yaml",
                    duration_seconds=300,
                    metrics_interval=30
                )

    def test_run_simulation_no_e2b(self):
        """Test running simulation without E2B."""
        # Setup
        state = {
            "manifest_path": "/path/to/manifest.yaml",
            "scenario": "network_latency",
            "severity": 50,
            "timeout": 300,
            "status": "in_progress"
        }

        # Mock HAS_E2B
        with mock.patch("arc_memory.simulate.langgraph_flow.HAS_E2B", False):
            # Execute
            result = run_simulation(state)

            # Verify
            assert result["simulation_results"] is not None
            assert result["metrics"] is not None
            assert result["risk_score"] is not None
            assert result["simulation_results"]["is_mock"] is True
            assert result["status"] == "in_progress"

    def test_run_simulation_no_manifest(self):
        """Test running simulation without a manifest."""
        # Setup
        state = {
            "scenario": "network_latency",
            "severity": 50,
            "timeout": 300,
            "status": "in_progress"
        }

        # Execute
        result = run_simulation(state)

        # Verify
        assert result["error"] is not None
        assert "No manifest" in result["error"]
        assert result["status"] == "failed"

    def test_create_embeddings_from_diff_success(self):
        """Test creating embeddings from diff data successfully."""
        # Setup
        state = {
            "diff_data": {
                "files": [
                    {
                        "path": "file1.py",
                        "content": "def hello():\n    return 'world'",
                        "change_type": "modified",
                        "hunks": [
                            {"content": "@@ -1,1 +1,2 @@\n-def hello()\n+def hello():\n+    return 'world'"}
                        ]
                    },
                    {
                        "path": "file2.py",
                        "content": "def goodbye():\n    return 'farewell'",
                        "change_type": "added"
                    }
                ]
            },
            "causal_graph": {
                "nodes": ["service1", "service2"],
                "edges": [{"source": "service1", "target": "service2"}]
            },
            "status": "in_progress"
        }

        # Execute
        result = create_embeddings_from_diff(state)

        # Verify
        assert result["context_documents"] is not None
        assert len(result["context_documents"]) == 4  # 2 file contents + 1 hunk + 1 causal graph
        assert result["status"] == "in_progress"

        # Check document types
        doc_types = [doc.metadata.get("type") for doc in result["context_documents"]]
        assert "file_content" in doc_types
        assert "diff_hunk" in doc_types
        assert "causal_graph" in doc_types

    def test_create_embeddings_from_diff_no_diff(self):
        """Test creating embeddings without diff data."""
        # Setup
        state = {
            "status": "in_progress"
        }

        # Execute
        result = create_embeddings_from_diff(state)

        # Verify
        assert "context_documents" not in result
        assert result["status"] == "in_progress"

    def test_generate_explanation_with_llm(self):
        """Test generating explanation with LLM."""
        # Setup
        state = {
            "rev_range": "HEAD~1..HEAD",
            "scenario": "network_latency",
            "severity": 50,
            "risk_score": 25,
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ]
            },
            "affected_services": ["service1", "service2"],
            "metrics": {
                "latency_ms": 500,
                "error_rate": 0.05,
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            },
            "context_documents": [
                mock.MagicMock(
                    page_content="def hello():\n    return 'world'",
                    metadata={"path": "file1.py", "type": "file_content"}
                ),
                mock.MagicMock(
                    page_content="@@ -1,1 +1,2 @@\n-def hello()\n+def hello():\n+    return 'world'",
                    metadata={"path": "file1.py", "type": "diff_hunk"}
                )
            ],
            "status": "in_progress"
        }

        # Mock get_llm and the chain invocation
        with mock.patch("arc_memory.simulate.langgraph_flow.get_llm") as mock_get_llm:
            mock_llm = mock.MagicMock()
            mock_chain = mock.MagicMock()
            mock_chain.invoke.return_value = mock.MagicMock(content="This is a test explanation.")

            # Mock OpenAIEmbeddings
            with mock.patch("arc_memory.simulate.langgraph_flow.OpenAIEmbeddings") as mock_embeddings:
                mock_embeddings_instance = mock.MagicMock()
                mock_embeddings_instance.embed_query.return_value = [0.1, 0.2, 0.3]
                mock_embeddings_instance.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
                mock_embeddings.return_value = mock_embeddings_instance

                # Mock the chain creation (prompt | llm)
                with mock.patch("arc_memory.simulate.langgraph_flow.ChatPromptTemplate") as mock_prompt:
                    mock_prompt.from_messages.return_value = mock.MagicMock()
                    mock_prompt.from_messages.return_value.__or__.return_value = mock_chain

                    mock_get_llm.return_value = mock_llm

                    # Execute
                    result = generate_explanation(state)

                    # Verify
                    assert result["explanation"] is not None
                    assert "This is a test explanation." in result["explanation"]
                    assert result["status"] == "in_progress"
                    mock_get_llm.assert_called_once()
                    mock_chain.invoke.assert_called_once()
                    mock_embeddings.assert_called()
                    mock_embeddings_instance.embed_query.assert_called_once()
                    mock_embeddings_instance.embed_documents.assert_called_once()

    def test_generate_explanation_no_llm(self):
        """Test generating explanation without LLM."""
        # Setup
        state = {
            "rev_range": "HEAD~1..HEAD",
            "scenario": "network_latency",
            "severity": 50,
            "risk_score": 25,
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ]
            },
            "affected_services": ["service1", "service2"],
            "metrics": {
                "latency_ms": 500,
                "error_rate": 0.05,
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            },
            "processed_metrics": {
                "latency_ms": 500,
                "error_rate": 0.05,
                "normalized_latency": 0.25,
                "normalized_error_rate": 0.05
            },
            "risk_factors": {
                "severity": 0.5,
                "service_count": 0.2,
                "normalized_latency": 0.25,
                "normalized_error_rate": 0.05
            },
            "status": "in_progress"
        }

        # Mock get_llm and the explanation generator
        with mock.patch("arc_memory.simulate.langgraph_flow.get_llm") as mock_get_llm:
            mock_get_llm.return_value = None

            # Mock the explanation generator
            with mock.patch("arc_memory.simulate.explanation.generate_explanation", return_value="Mocked explanation") as mock_generate:
                # Execute
                result = generate_explanation(state)

                # Verify
                assert result["explanation"] is not None
                assert result["explanation"] == "Mocked explanation"
                assert result["status"] == "in_progress"
                mock_get_llm.assert_called_once()
                mock_generate.assert_called_once()

    def test_generate_attestation_success(self):
        """Test generating attestation successfully."""
        # Setup
        state = {
            "diff_data": {
                "files": [
                    {"path": "file1.py", "additions": 10, "deletions": 5},
                    {"path": "file2.py", "additions": 20, "deletions": 15}
                ],
                "end_commit": "abc123",
                "timestamp": "2023-01-01T00:00:00Z"
            },
            "metrics": {
                "latency_ms": 500,
                "error_rate": 0.05,
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            },
            "manifest": {
                "metadata": {
                    "annotations": {
                        "arc-memory.io/manifest-hash": "def456"
                    }
                }
            },
            "risk_score": 25,
            "explanation": "This is a test explanation.",
            "rev_range": "HEAD~1..HEAD",
            "scenario": "network_latency",
            "severity": 50,
            "affected_services": ["service1", "service2"],
            "status": "in_progress"
        }

        # Mock the attestation generator
        mock_attestation = {
            "sim_id": "sim_HEAD~1_HEAD",
            "manifest_hash": "def456",
            "commit_target": "abc123",
            "risk_score": 25,
            "explanation": "This is a test explanation."
        }

        with mock.patch("arc_memory.simulate.langgraph_flow.generate_and_save_attestation", return_value=mock_attestation) as mock_generate:
            # Execute
            result = generate_attestation(state)

            # Verify
            assert result["attestation"] is not None
            assert result["attestation"]["sim_id"] == "sim_HEAD~1_HEAD"
            assert result["attestation"]["manifest_hash"] == "def456"
            assert result["attestation"]["commit_target"] == "abc123"
            assert result["attestation"]["risk_score"] == 25
            assert result["attestation"]["explanation"] == "This is a test explanation."
            assert result["status"] == "completed"
            mock_generate.assert_called_once()

    def test_generate_attestation_missing_data(self):
        """Test generating attestation with missing data."""
        # Setup - missing diff_data
        state = {
            "metrics": {
                "latency_ms": 500,
                "error_rate": 0.05,
                "node_count": 1,
                "pod_count": 5,
                "service_count": 3
            },
            "manifest": {
                "metadata": {
                    "annotations": {
                        "arc-memory.io/manifest-hash": "def456"
                    }
                }
            },
            "risk_score": 25,
            "explanation": "This is a test explanation.",
            "rev_range": "HEAD~1..HEAD",
            "status": "in_progress"
        }

        # Execute
        result = generate_attestation(state)

        # Verify
        assert result["error"] is not None
        assert "No diff data" in result["error"]
        assert result["status"] == "failed"

    def test_should_continue(self):
        """Test the should_continue function."""
        # Test with in_progress status
        state = {"status": "in_progress"}
        assert should_continue(state) == "continue"

        # Test with failed status
        state = {"status": "failed"}
        assert should_continue(state) == "end"

        # Test with completed status
        state = {"status": "completed"}
        assert should_continue(state) == "continue"

    def test_create_workflow(self):
        """Test creating the workflow."""
        # Execute
        workflow = create_workflow()

        # Verify
        assert workflow is not None

        # Test with a mock StateGraph to verify nodes
        with mock.patch("arc_memory.simulate.langgraph_flow.StateGraph") as mock_state_graph:
            mock_graph = mock.MagicMock()
            mock_state_graph.return_value = mock_graph

            # Call create_workflow
            create_workflow()

            # Verify that all nodes are added
            assert mock_graph.add_node.call_count >= 8  # At least 8 nodes

            # Check that our new node is added
            mock_graph.add_node.assert_any_call("create_embeddings", create_embeddings_from_diff)

            # Check that the edge from run_simulation to create_embeddings exists
            mock_graph.add_edge.assert_any_call("run_simulation", "create_embeddings")

            # Check that the edge from create_embeddings to generate_explanation exists
            mock_graph.add_edge.assert_any_call("create_embeddings", "generate_explanation")

    def test_run_sim_success(self):
        """Test running the simulation workflow successfully."""
        # Mock create_workflow and workflow.invoke
        with mock.patch("arc_memory.simulate.langgraph_flow.create_workflow") as mock_create_workflow:
            mock_workflow = mock.MagicMock()
            mock_workflow.invoke.return_value = {
                "status": "completed",
                "attestation": {
                    "sim_id": "sim_HEAD~1_HEAD",
                    "manifest_hash": "def456",
                    "commit_target": "abc123",
                    "risk_score": 25,
                    "explanation": "This is a test explanation."
                },
                "explanation": "This is a test explanation.",
                "risk_score": 25,
                "metrics": {
                    "latency_ms": 500,
                    "error_rate": 0.05
                },
                "affected_services": ["service1", "service2"],
                "rev_range": "HEAD~1..HEAD"
            }
            mock_create_workflow.return_value = mock_workflow

            # Execute
            result = run_sim("HEAD~1..HEAD")

            # Verify
            assert result["status"] == "completed"
            assert result["attestation"] is not None
            assert result["explanation"] is not None
            assert result["risk_score"] == 25
            assert result["metrics"] is not None
            assert result["affected_services"] == ["service1", "service2"]
            assert result["rev_range"] == "HEAD~1..HEAD"
            mock_create_workflow.assert_called_once()
            mock_workflow.invoke.assert_called_once()

    def test_run_sim_failure(self):
        """Test running the simulation workflow with failure."""
        # Mock create_workflow and workflow.invoke
        with mock.patch("arc_memory.simulate.langgraph_flow.create_workflow") as mock_create_workflow:
            mock_workflow = mock.MagicMock()
            mock_workflow.invoke.return_value = {
                "status": "failed",
                "error": "Test error",
                "rev_range": "HEAD~1..HEAD"
            }
            mock_create_workflow.return_value = mock_workflow

            # Execute
            result = run_sim("HEAD~1..HEAD")

            # Verify
            assert result["status"] == "failed"
            assert result["error"] == "Test error"
            assert result["rev_range"] == "HEAD~1..HEAD"
            mock_create_workflow.assert_called_once()
            mock_workflow.invoke.assert_called_once()

    def test_run_sim_exception(self):
        """Test running the simulation workflow with an exception."""
        # Mock create_workflow
        with mock.patch("arc_memory.simulate.langgraph_flow.create_workflow") as mock_create_workflow:
            mock_create_workflow.side_effect = Exception("Test error")

            # Execute
            result = run_sim("HEAD~1..HEAD")

            # Verify
            assert result["status"] == "failed"
            assert "Test error" in result["error"]
            assert result["rev_range"] == "HEAD~1..HEAD"
            mock_create_workflow.assert_called_once()

    def test_get_llm_success(self):
        """Test getting the LLM successfully."""
        # Mock os.environ and ChatOpenAI
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with mock.patch("arc_memory.simulate.langgraph_flow.ChatOpenAI") as mock_chat_openai:
                mock_llm = mock.MagicMock()
                mock_chat_openai.return_value = mock_llm

                # Execute
                llm = get_llm()

                # Verify
                assert llm is not None
                assert llm == mock_llm
                mock_chat_openai.assert_called_once_with(
                    model="gpt-4.1-2025-04-14",
                    temperature=0.1,
                    api_key="test-key"
                )

    def test_get_llm_no_api_key(self):
        """Test getting the LLM without an API key."""
        # Mock os.environ
        with mock.patch.dict(os.environ, {}, clear=True):
            # Execute
            llm = get_llm()

            # Verify
            assert llm is None

    def test_get_llm_exception(self):
        """Test getting the LLM with an exception."""
        # Mock os.environ and ChatOpenAI
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with mock.patch("arc_memory.simulate.langgraph_flow.ChatOpenAI") as mock_chat_openai:
                mock_chat_openai.side_effect = Exception("Test error")

                # Execute
                llm = get_llm()

                # Verify
                assert llm is None
                mock_chat_openai.assert_called_once()
