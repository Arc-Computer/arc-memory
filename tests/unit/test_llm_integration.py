"""Unit tests for LLM integration with Ollama."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = OllamaClient()
    client.session = MagicMock()
    return client


def test_ollama_client_initialization():
    """Test that the Ollama client initializes correctly."""
    client = OllamaClient()
    assert client.host == "http://localhost:11434"
    assert isinstance(client.session, requests.Session)


@patch("requests.post")
def test_generate(mock_post, mock_ollama_client):
    """Test the generate method."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Test response"}
    mock_post.return_value = mock_response

    # Call the method
    response = mock_ollama_client.generate(
        model="gemma3:27b-it-qat",
        prompt="Test prompt",
        options={"temperature": 0.7}
    )

    # Verify the response
    assert response == "Test response"

    # Verify the request
    mock_post.assert_called_once()


@patch("requests.post")
def test_generate_error(mock_post, mock_ollama_client):
    """Test error handling in the generate method."""
    # Setup mock response to raise an exception
    mock_post.side_effect = requests.exceptions.RequestException("Test error")

    # Call the method and check that it returns an error message
    response = mock_ollama_client.generate(
        model="gemma3:27b-it-qat",
        prompt="Test prompt"
    )

    # The generate method should catch the exception and return an error message
    assert "Error:" in response


def test_ensure_model_available_already_available(mock_ollama_client):
    """Test ensure_model_available when the model is already available."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Mock the session
    mock_ollama_client.session = MagicMock()
    mock_ollama_client.session.post.return_value = mock_response

    # Call the method
    result = mock_ollama_client.ensure_model_available("phi4-mini-reasoning")

    # Verify the result
    assert result is True

    # Verify the request
    mock_ollama_client.session.post.assert_called_once_with(
        "http://localhost:11434/api/show",
        json={"name": "phi4-mini-reasoning"}
    )


def test_ensure_model_available_pull_needed(mock_ollama_client):
    """Test ensure_model_available when the model needs to be pulled."""
    # Setup mock responses
    mock_show_response = MagicMock()
    mock_show_response.status_code = 404

    mock_pull_response = MagicMock()
    mock_pull_response.status_code = 200
    mock_pull_response.iter_lines.return_value = [
        json.dumps({"status": "downloading", "completed": 50, "total": 100}).encode(),
        json.dumps({"status": "success"}).encode()
    ]

    # Mock the session
    mock_ollama_client.session = MagicMock()
    mock_ollama_client.session.post.side_effect = [mock_show_response, mock_pull_response]

    # Call the method
    result = mock_ollama_client.ensure_model_available("phi4-mini-reasoning")

    # Verify the result
    assert result is True

    # Verify the requests
    assert mock_ollama_client.session.post.call_count == 2
    mock_ollama_client.session.post.assert_any_call(
        "http://localhost:11434/api/show",
        json={"name": "phi4-mini-reasoning"}
    )
    mock_ollama_client.session.post.assert_any_call(
        "http://localhost:11434/api/pull",
        json={"name": "phi4-mini-reasoning"},
        stream=True
    )


@patch("arc_memory.llm.ollama_client.subprocess.run")
@patch("arc_memory.llm.ollama_client.subprocess.Popen")
@patch("arc_memory.llm.ollama_client.requests.get")
@patch("arc_memory.llm.ollama_client.OllamaClient")
def test_ensure_ollama_available_installed_running(mock_client_class, mock_get, mock_popen, mock_run):
    """Test ensure_ollama_available when Ollama is installed and running."""
    # Setup mocks
    mock_run.return_value = MagicMock()
    mock_run.return_value.stdout = "/usr/local/bin/ollama"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    mock_client = MagicMock()
    mock_client.ensure_model_available.return_value = True
    mock_client_class.return_value = mock_client

    # Call the function
    result = ensure_ollama_available()

    # Verify the result
    assert result is True

    # Verify the calls
    mock_run.assert_called_once()
    mock_get.assert_called_once_with("http://localhost:11434/api/version")
    mock_popen.assert_not_called()
    mock_client.ensure_model_available.assert_called_once_with("gemma3:27b-it-qat")


@patch("arc_memory.llm.ollama_client.subprocess.run")
@patch("arc_memory.llm.ollama_client.subprocess.Popen")
@patch("arc_memory.llm.ollama_client.requests.get")
@patch("arc_memory.llm.ollama_client.OllamaClient")
def test_ensure_ollama_available_installed_not_running(
    mock_client_class, mock_get, mock_popen, mock_run
):
    """Test ensure_ollama_available when Ollama is installed but not running."""
    # Setup mocks
    mock_run.return_value = MagicMock()
    mock_run.return_value.stdout = "/usr/local/bin/ollama"

    # First call raises exception (not running), second call succeeds (now running)
    mock_get.side_effect = [requests.ConnectionError(), MagicMock(status_code=200)]

    mock_client = MagicMock()
    mock_client.ensure_model_available.return_value = True
    mock_client_class.return_value = mock_client

    # Call the function
    result = ensure_ollama_available()

    # Verify the result
    assert result is True

    # Verify the calls
    mock_run.assert_called_once()
    assert mock_get.call_count == 2
    mock_popen.assert_called_once()
    mock_client.ensure_model_available.assert_called_once_with("gemma3:27b-it-qat")


@patch("arc_memory.llm.ollama_client.subprocess.run")
@patch("arc_memory.llm.ollama_client.os.environ.get")
@patch("arc_memory.llm.ollama_client.requests.get")
@patch("arc_memory.llm.ollama_client.subprocess.Popen")
def test_ensure_ollama_available_not_installed_ci(mock_popen, mock_get, mock_environ_get, mock_run):
    """Test ensure_ollama_available when Ollama is not installed in CI."""
    # Setup mocks
    mock_run.return_value = MagicMock()
    mock_run.return_value.stdout = ""
    mock_environ_get.return_value = "true"  # CI environment

    # Mock subprocess.run for curl
    mock_curl_result = MagicMock()
    mock_curl_result.stdout = "echo 'Mock install script'"
    mock_run.side_effect = [mock_run.return_value, mock_curl_result]

    # Mock subprocess.Popen to avoid actual process creation
    mock_popen.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'ollama'")

    # Call the function
    result = ensure_ollama_available()

    # Verify the result
    assert result is False  # Should fail in this test case

    # Verify the calls
    assert mock_run.call_count >= 1
    mock_environ_get.assert_called_with("CI")
