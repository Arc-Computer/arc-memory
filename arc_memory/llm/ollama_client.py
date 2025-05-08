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

    def generate(self, model: str, prompt: str, options: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> str:
        """Generate a response from Ollama.

        Args:
            model: The model to use for generation.
            prompt: The prompt to send to the model.
            options: Optional parameters for generation (temperature, etc.).
            system_prompt: Optional system prompt to guide the model's behavior.

        Returns:
            The generated response as a string.

        Raises:
            Exception: If there's an error communicating with Ollama.
        """
        url = f"{self.host}/api/generate"

        data = {
            "model": model,
            "prompt": prompt,
            "options": options or {}
        }
        
        # Add system prompt if provided
        if system_prompt:
            # Format according to Qwen3 model expectations
            data["system"] = system_prompt
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            # For streaming responses
            if 'Content-Type' in response.headers and 'application/x-ndjson' in response.headers['Content-Type']:
                # Handle streaming response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                full_response += data["response"]
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing streaming line: {e}")
                return full_response
            
            # For regular JSON responses
            try:
                return response.json()["response"]
            except (json.JSONDecodeError, KeyError) as e:
                # Handle malformed JSON or missing "response" key
                logger.error(f"Error parsing Ollama response: {e}")
                # Extract text content as fallback
                if response.text:
                    # Try to extract just the content part if there's extra data
                    try:
                        # First attempt: try to parse the first valid JSON object
                        content_lines = response.text.strip().split('\n')
                        for line in content_lines:
                            try:
                                json_obj = json.loads(line)
                                if "response" in json_obj:
                                    return json_obj["response"]
                            except:
                                continue
                        
                        # Second attempt: if the response starts with a valid JSON object
                        # but has extra content, try to parse just the first part
                        first_json_end = response.text.find('}\n')
                        if first_json_end > 0:
                            try:
                                json_obj = json.loads(response.text[:first_json_end+1])
                                if "response" in json_obj:
                                    return json_obj["response"]
                            except:
                                pass
                        
                        # Last resort: return the raw text
                        logger.info(f"Using raw response text as fallback (first 100 chars): {response.text[:100]}...")
                        return response.text
                    except Exception as parse_error:
                        logger.error(f"Error parsing content: {parse_error}")
                        return response.text
                raise ValueError(f"Failed to parse response from Ollama: {e}")
                
        except requests.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating response from Ollama: {e}")
            raise

    def generate_with_thinking(self, model: str, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response using the thinking mode in Qwen3.

        Args:
            model: The model to use for generation (should be Qwen3 model).
            prompt: The prompt to send to the model.
            options: Optional parameters for generation.

        Returns:
            The generated response with thinking.
        """
        # Add thinking directive explicitly for Qwen3 models
        if not prompt.endswith("/think") and not "/think" in prompt:
            prompt = f"{prompt} /think"
            
        return self.generate(model, prompt, options)

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


def ensure_ollama_available(model: str = "qwen3:4b") -> bool:
    """Ensure Ollama and the required model are available.

    This function checks if Ollama is installed and running, and if the
    specified model is available. If Ollama is not installed, it attempts
    to install it. If the model is not available, it attempts to pull it.

    Args:
        model: The model to ensure is available.

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
                    "Ollama not found. Please install Ollama: https://ollama.com/download"
                )
                return False
        except Exception as e:
            logger.error(f"Failed to install Ollama: {e}")
            return False

    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code != 200:
            logger.info("Ollama is installed but not running, attempting to start...")
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Wait for Ollama to start
            for _ in range(10):
                try:
                    response = requests.get("http://localhost:11434/api/version")
                    if response.status_code == 200:
                        logger.info("Ollama started successfully")
                        break
                except:
                    pass
                time.sleep(1)
            else:
                logger.error("Failed to start Ollama")
                return False
    except:
        logger.info("Ollama is installed but not running, attempting to start...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Wait for Ollama to start
        for _ in range(10):
            try:
                response = requests.get("http://localhost:11434/api/version")
                if response.status_code == 200:
                    logger.info("Ollama started successfully")
                    break
            except:
                pass
            time.sleep(1)
        else:
            logger.error("Failed to start Ollama")
            return False

    # Check if model is available and pull if needed
    client = OllamaClient()
    return client.ensure_model_available(model)
