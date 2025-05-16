"""OpenAI client for Arc Memory.

This module provides a client for interacting with OpenAI's API.
It is used for enhancing the knowledge graph with LLM-derived insights.

This implementation uses the latest OpenAI API (v1) patterns as documented at:
https://platform.openai.com/docs/guides/text-generation
"""

import os
import json
import time
from typing import Any, Dict, List, Optional, Union, Iterator

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)

# Import OpenAI conditionally to avoid hard dependency
try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionChunk
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. Install with 'pip install openai'")


class OpenAIClient:
    """Client for interacting with OpenAI's API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI client.

        Args:
            api_key: The OpenAI API key. If None, uses the OPENAI_API_KEY environment variable.
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Install with 'pip install openai'"
            )

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set the OPENAI_API_KEY environment variable "
                "or pass the api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)

    def generate(
        self,
        model: str = None,
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260,
    ) -> str:
        """Generate text using the specified model.

        Args:
            model: The model to use. If None, uses OPENAI_MODEL env var or defaults to gpt-4.1.
                  Available models: gpt-4.1, o4-mini
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Additional options to pass to the model.
                     Can include: temperature, max_tokens, top_p, frequency_penalty,
                     presence_penalty, response_format (for JSON mode)
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The generated text.
        """
        # Set default model if not provided
        if model is None:
            model = os.environ.get("OPENAI_MODEL", "gpt-4.1")

        # Set default options if not provided
        if options is None:
            options = {}

        # Set default system prompt if not provided
        if system is None:
            system = """You are a helpful AI assistant specialized in software engineering and code analysis.
You provide clear, concise, and accurate information about code, software architecture, and development practices.
When analyzing code or development artifacts, focus on:
1. The purpose and functionality of the code
2. Relationships between components
3. Potential issues or improvements
4. Historical context and design decisions

Always base your responses on the specific information provided, and avoid making assumptions unless explicitly stated.
"""

        # Check if the prompt is asking for JSON
        is_json_request = False
        if "JSON" in prompt and ("format" in prompt.lower() or "structure" in prompt.lower()):
            is_json_request = True
            logger.debug("Detected JSON request in prompt")

            # For JSON requests, prefer GPT-4.1 over o4-mini
            if model == "o4-mini":
                model = "gpt-4.1"
                logger.info("Switching from o4-mini to gpt-4.1 for JSON request to ensure proper formatting")

        # Add explicit JSON formatting instructions for all JSON requests
        if is_json_request:
            # Enhance the system prompt with explicit JSON formatting instructions
            system = f"""{system}

When returning JSON:
1. Always use double quotes for keys and string values
2. Always include commas between key-value pairs
3. Never include trailing commas
4. Format the JSON properly with correct indentation
5. Ensure all brackets and braces are properly closed
6. Return ONLY valid JSON without any additional text
"""
            logger.debug("Enhanced system prompt with JSON formatting instructions")

        # Prepare messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Extract relevant options
        temperature = options.get("temperature", 0.3)
        max_tokens = options.get("max_tokens", None)
        top_p = options.get("top_p", None)
        frequency_penalty = options.get("frequency_penalty", None)
        presence_penalty = options.get("presence_penalty", None)
        response_format = options.get("response_format", None)

        # Set up parameters for the API call
        params = {
            "model": model,
            "messages": messages,
            "timeout": timeout
        }

        # o4-mini does not support temperature parameter (only default value of 1.0)
        if not model == "o4-mini":
            params["temperature"] = temperature

        # Add optional parameters only if they are provided
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if top_p is not None:
            params["top_p"] = top_p
        if frequency_penalty is not None:
            params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            params["presence_penalty"] = presence_penalty

        # Add response format for JSON requests
        if is_json_request and model in ["gpt-4.1", "o4-mini"]:
            # These models support the JSON response format parameter
            params["response_format"] = {"type": "json_object"}
            logger.debug(f"Set response_format=json_object for {model}")
        # Add response format if explicitly specified
        elif response_format is not None:
            params["response_format"] = response_format

        try:
            # Send the request
            start_time = time.time()
            response = self.client.chat.completions.create(**params)
            elapsed_time = time.time() - start_time
            logger.debug(f"OpenAI API call took {elapsed_time:.2f} seconds")

            # Return the response content
            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return f"Error: {e}"

    def generate_with_streaming(
        self,
        model: str = None,
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
        # Set default options if not provided
        if options is None:
            options = {}

        # Set default system prompt if not provided
        if system is None:
            system = """You are a helpful AI assistant specialized in software engineering and code analysis.
You provide clear, concise, and accurate information about code, software architecture, and development practices.
When analyzing code or development artifacts, focus on:
1. The purpose and functionality of the code
2. Relationships between components
3. Potential issues or improvements
4. Historical context and design decisions

Always base your responses on the specific information provided, and avoid making assumptions unless explicitly stated.
"""

        # Prepare messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Extract relevant options
        temperature = options.get("temperature", 0.3)
        max_tokens = options.get("max_tokens", None)
        top_p = options.get("top_p", None)
        frequency_penalty = options.get("frequency_penalty", None)
        presence_penalty = options.get("presence_penalty", None)
        response_format = options.get("response_format", None)

        # Set up parameters for the API call
        params = {
            "model": model,
            "messages": messages,
            "timeout": timeout,
            "stream": True
        }

        # Only add temperature if not using o4-mini (which only supports default temperature)
        if not model.startswith("o4-mini"):
            params["temperature"] = temperature

        # Check if this is a JSON request
        is_json_request = False
        if "JSON" in prompt and ("format" in prompt.lower() or "structure" in prompt.lower()):
            is_json_request = True
            logger.debug("Detected JSON request in streaming prompt")

            # For JSON requests, prefer GPT-4.1 over o4-mini
            if model == "o4-mini":
                model = "gpt-4.1"
                params["model"] = "gpt-4.1"
                logger.info("Switching from o4-mini to gpt-4.1 for JSON streaming request")

            # Add response format for JSON requests with supported models
            if model in ["gpt-4.1", "gpt-4", "gpt-3.5-turbo"]:
                params["response_format"] = {"type": "json_object"}
                logger.debug(f"Set response_format=json_object for streaming with {model}")

        # Add optional parameters only if they are provided
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if top_p is not None:
            params["top_p"] = top_p
        if frequency_penalty is not None:
            params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            params["presence_penalty"] = presence_penalty

        # Add response format if specified (for JSON mode)
        if response_format is not None:
            params["response_format"] = response_format

        try:
            # Send the request with streaming
            start_time = time.time()
            response_stream = self.client.chat.completions.create(**params)

            # Collect the entire response
            full_response = ""
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content

            elapsed_time = time.time() - start_time
            logger.debug(f"OpenAI API streaming call took {elapsed_time:.2f} seconds")

            return full_response

        except Exception as e:
            logger.error(f"Error calling OpenAI API with streaming: {e}")
            return f"Error: {e}"

    def generate_with_thinking(
        self,
        model: str = None,
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260
    ) -> str:
        """Generate a response using the thinking mode.

        Args:
            model: The model to use for generation.
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Optional parameters for generation.
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The generated response with thinking.
        """
        # Check if this is a JSON request
        is_json_request = False
        if "JSON" in prompt and ("format" in prompt.lower() or "structure" in prompt.lower()):
            is_json_request = True
            logger.debug("Detected JSON request in thinking prompt")

            # For JSON requests, prefer GPT-4.1 over o4-mini
            if model == "o4-mini":
                model = "gpt-4.1"
                logger.info("Switching from o4-mini to gpt-4.1 for JSON thinking request")

        # Modify the system prompt to include instructions for thinking
        if system:
            enhanced_system = f"""{system}

When answering, first think step by step about the problem, then provide your final answer.
Structure your response like this:

Thinking:
<your step-by-step reasoning process>

Answer:
<your final answer>
"""
        else:
            enhanced_system = """You are a helpful AI assistant specialized in software engineering and code analysis.
You provide clear, concise, and accurate information about code, software architecture, and development practices.

When answering, first think step by step about the problem, then provide your final answer.
Structure your response like this:

Thinking:
<your step-by-step reasoning process>

Answer:
<your final answer>
"""

        # For JSON requests, add specific instructions
        if is_json_request:
            enhanced_system += """

When returning JSON in your Answer section:
1. Always use double quotes for keys and string values
2. Always include commas between key-value pairs
3. Never include trailing commas
4. Format the JSON properly with correct indentation
5. Ensure all brackets and braces are properly closed
6. Return ONLY valid JSON in the Answer section without any additional text
"""
            logger.debug("Added JSON formatting instructions to thinking prompt")

        # Update options for JSON requests
        if is_json_request and options is None:
            options = {}

        # Generate the response with the enhanced system prompt
        return self.generate(
            model=model,
            prompt=prompt,
            system=enhanced_system,
            options=options,
            timeout=timeout
        )


def ensure_openai_available(api_key: Optional[str] = None) -> bool:
    """Check if OpenAI is available and configured.

    Args:
        api_key: Optional API key to use. If None, uses the OPENAI_API_KEY environment variable.

    Returns:
        True if OpenAI is available and configured, False otherwise.
    """
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI package not installed. Install with 'pip install openai'")
        return False

    # Check if API key is provided or in environment
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return False

    # Test the API with a simple query
    try:
        client = OpenAIClient(api_key=api_key)
        # Use model from environment variable if set, otherwise use default
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1")

        # Set options based on model
        options = {}
        if model != "o4-mini":
            options["temperature"] = 0.0

        response = client.generate(
            model=model,
            prompt="Respond with a single word: Working",
            options=options
        )
        if "working" in response.lower():
            logger.info("OpenAI API is working correctly.")
            return True
        else:
            # Suppressed warning to avoid cluttering demo output
            # logger.warning(f"OpenAI API returned unexpected response: {response[:50]}...")
            return False
    except Exception as e:
        logger.warning(f"Failed to connect to OpenAI API: {e}")
        return False
