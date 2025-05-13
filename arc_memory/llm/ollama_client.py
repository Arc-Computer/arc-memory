"""Ollama client for Arc Memory.

This module provides a client for interacting with Ollama, a local LLM server.
It is used for enhancing the knowledge graph with LLM-derived insights.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Client for interacting with Ollama."""

    def __init__(self, host: str = "http://localhost:11434"):
        """Initialize the Ollama client.

        Args:
            host: The host URL for the Ollama API.
        """
        self.host = host
        self.session = requests.Session()

    def generate(
        self,
        model: str = "qwen3:4b",
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260,
    ) -> str:
        """Generate text using the specified model.

        Args:
            model: The model to use.
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Additional options to pass to the model.
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The generated text.
        """
        url = f"{self.host}/api/generate"

        # Set default options if not provided
        if options is None:
            options = {}

        # Set default system prompt if not provided
        if system is None:
            system = """You are a helpful AI assistant specialized in software engineering and code analysis.

You have access to a knowledge graph with the following schema:
- Nodes have a dedicated timestamp column for efficient temporal queries
- Each node has a type (COMMIT, FILE, PR, ISSUE, ADR, etc.)
- Each node has a normalized timestamp (ts) field
- Timestamps are stored in ISO format and indexed for efficient querying
- Temporal relationships like PRECEDES are created between nodes based on their timestamps
- The knowledge graph supports bi-temporal analysis (as-of and as-at time dimensions)"""

        # Format the request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "options": options,
            "stream": False  # Default to non-streaming for simplicity
        }

        try:
            # Send the request
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            return data.get("response", "")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            return f"Error: {e}"
        except ValueError as e:
            logger.error(f"Error parsing Ollama response: {e}")
            return f"Error parsing response: {e}"

    def generate_with_streaming(
        self,
        model: str = "qwen3:4b",
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260,
    ) -> str:
        """Generate text using the specified model with streaming.

        This method is especially useful for larger responses like JSON
        where we want to collect the entire response properly.

        Args:
            model: The model to use.
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Additional options to pass to the model.
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The complete generated text from the stream.
        """
        url = f"{self.host}/api/generate"

        # Set default options if not provided
        if options is None:
            options = {}

        # Set default system prompt if not provided
        if system is None:
            system = """You are a helpful AI assistant specialized in software engineering and code analysis.

You have access to a knowledge graph with the following schema:
- Nodes have a dedicated timestamp column for efficient temporal queries
- Each node has a type (COMMIT, FILE, PR, ISSUE, ADR, etc.)
- Each node has a normalized timestamp (ts) field
- Timestamps are stored in ISO format and indexed for efficient querying
- Temporal relationships like PRECEDES are created between nodes based on their timestamps
- The knowledge graph supports bi-temporal analysis (as-of and as-at time dimensions)"""

        # Format the request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "options": options,
            "stream": True  # Enable streaming
        }

        try:
            # Send the request
            response = requests.post(url, json=payload, stream=True, timeout=timeout)
            response.raise_for_status()

            # Collect the streamed response
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        # Decode the line
                        line_text = line.decode('utf-8')

                        # Skip empty lines
                        if not line_text.strip():
                            continue

                        # Parse the JSON
                        line_data = json.loads(line_text)

                        # Add the response text to the full response
                        if "response" in line_data:
                            full_response += line_data["response"]

                        # Check if done
                        if line_data.get("done", False):
                            break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error parsing streaming response line: {e}")
                        continue

            return full_response

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            return f"Error: {e}"
        except ValueError as e:
            logger.error(f"Error parsing Ollama streaming response: {e}")
            return f"Error parsing response: {e}"

    def generate_with_thinking(
        self,
        model: str = "qwen3:4b",
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260
    ) -> str:
        """Generate a response using the thinking mode in Qwen3.

        Args:
            model: The model to use for generation (should be Qwen3 model).
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Optional parameters for generation.
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The generated response with thinking.
        """
        # Modify the system prompt to include instructions for thinking and JSON format
        if system:
            enhanced_system = f"""{system}

When reasoning through complex questions, first wrap your detailed thinking in <think> tags like this:
<think>
Your detailed reasoning process goes here...
</think>

After your thinking, provide your final response in valid JSON format surrounded by triple backticks:
```json
{{
  "your": "json response"
}}
```

This separation ensures your detailed reasoning process is captured while making the final JSON easy to parse."""
        else:
            enhanced_system = """You are a helpful AI assistant specialized in software engineering and code analysis.

You have access to a knowledge graph with the following schema:
- Nodes have a dedicated timestamp column for efficient temporal queries
- Each node has a type (COMMIT, FILE, PR, ISSUE, ADR, etc.)
- Each node has a normalized timestamp (ts) field
- Timestamps are stored in ISO format and indexed for efficient querying
- Temporal relationships like PRECEDES are created between nodes based on their timestamps
- The knowledge graph supports bi-temporal analysis (as-of and as-at time dimensions)

When reasoning through complex questions, first wrap your detailed thinking in <think> tags like this:
<think>
Your detailed reasoning process goes here...
</think>

After your thinking, provide your final response in valid JSON format surrounded by triple backticks:
```json
{{
  "your": "json response"
}}
```

This separation ensures your detailed reasoning process is captured while making the final JSON easy to parse.

When analyzing temporal data, consider:
1. The chronological order of events based on normalized timestamps
2. The relationships between events that occurred close in time
3. Patterns of changes over time that might indicate development phases
4. The evolution of code entities over time based on their modification history"""

        # Use our normal generate method with the enhanced system prompt
        # and instruct the model to think step by step
        return self.generate(
            model=model,
            prompt=f"{prompt} (Think step by step, then provide your final answer as valid JSON.)",
            system=enhanced_system,
            options=options,
            timeout=timeout
        )

    def ensure_model_available(self, model: str) -> bool:
        """Ensure the specified model is available, pulling if needed.

        Args:
            model: The model to check for availability.

        Returns:
            True if the model is available, False otherwise.

        Raises:
            Exception: If there's an error pulling the model.
        """
        url = f"{self.host}/api/show"

        try:
            response = self.session.post(url, json={"name": model})
            if response.status_code == 200:
                logger.info(f"Model {model} is already available")
                return True
        except Exception as e:
            logger.warning(f"Error checking model availability: {e}")

        # Model not available, pull it
        logger.info(f"Pulling model {model}...")
        url = f"{self.host}/api/pull"

        try:
            response = self.session.post(url, json={"name": model}, stream=True)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "error" in data:
                        logger.error(f"Error pulling model: {data['error']}")
                        return False

                    if "status" in data and data["status"] == "success":
                        logger.info(f"Successfully pulled model {model}")
                        return True

                    # Log progress
                    if "completed" in data and "total" in data:
                        progress = (data["completed"] / data["total"]) * 100
                        logger.info(f"Pulling model {model}: {progress:.1f}% complete")

            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False
def ensure_ollama_available(model: str = "qwen3:4b", timeout: int = 60) -> bool:
    """Ensure Ollama and the required model are available.

    This function checks if Ollama is installed and running, and if the
    specified model is available. If Ollama is not installed, it attempts
    to install it. If the model is not available, it attempts to pull it.

    Args:
        model: The model to ensure is available.
        timeout: Maximum time in seconds to wait for Ollama to respond.

    Returns:
        True if Ollama and the model are available, False otherwise.

    Raises:
        RuntimeError: If Ollama cannot be installed or the model cannot be pulled.
    """
    # Check if Ollama is installed
    ollama_path = subprocess.run(
        ["which", "ollama"], capture_output=True, text=True
    ).stdout.strip()

    if not ollama_path:
        logger.info("Ollama not found, attempting to install...")
        try:
            # Check if we're in a CI environment
            if os.environ.get("CI") == "true":
                # In CI, we can install Ollama automatically
                install_script = subprocess.run(
                    ["curl", "-fsSL", "https://ollama.com/install.sh"],
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["sh"], input=install_script.stdout, capture_output=True, text=True
                )
            else:
                # In a local environment, prompt the user
                logger.error(
                    "Ollama not found. Please install Ollama from https://ollama.ai/download "
                    "and run 'ollama serve' to start the Ollama server. "
                    "Then run 'ollama pull qwen3:4b' to download the default model."
                )
                return False
        except Exception as e:
            logger.error(f"Failed to install Ollama: {e}")
            return False

    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=min(5, timeout))
        if response.status_code != 200:
            logger.info("Ollama is installed but not running, attempting to start...")
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Wait for Ollama to start
            max_attempts = max(1, timeout // 2)  # Use half the timeout for waiting
            for _ in range(max_attempts):
                try:
                    response = requests.get("http://localhost:11434/api/version", timeout=min(2, timeout))
                    if response.status_code == 200:
                        logger.info("Ollama started successfully")
                        break
                except:
                    pass
                time.sleep(1)
            else:
                logger.error("Failed to start Ollama within timeout period")
                return False
    except requests.RequestException:
        logger.info("Ollama is installed but not running, attempting to start...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Wait for Ollama to start
        max_attempts = max(1, timeout // 2)  # Use half the timeout for waiting
        for _ in range(max_attempts):
            try:
                response = requests.get("http://localhost:11434/api/version", timeout=min(2, timeout))
                if response.status_code == 200:
                    logger.info("Ollama started successfully")
                    break
            except:
                pass
            time.sleep(1)
        else:
            logger.error("Failed to start Ollama within timeout period")
            return False

    # Check if model is available and pull if needed
    client = OllamaClient()
    return client.ensure_model_available(model)
