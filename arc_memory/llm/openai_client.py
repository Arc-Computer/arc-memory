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
        model: str = "gpt-4.1",
        prompt: str = "",
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 260,
    ) -> str:
        """Generate text using the specified model.

        Args:
            model: The model to use (defaults to gpt-4.1, the latest flagship model).
                  Available models: gpt-4.1
            prompt: The prompt to send to the model.
            system: The system message to use.
            options: Additional options to pass to the model.
                     Can include: temperature, max_tokens, top_p, frequency_penalty,
                     presence_penalty, response_format (for JSON mode)
            timeout: Maximum time in seconds to wait for the model to respond.

        Returns:
            The generated text.
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
            "temperature": temperature,
            "timeout": timeout
        }

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
        model: str = "gpt-4.1",
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
            "temperature": temperature,
            "timeout": timeout,
            "stream": True
        }

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
        model: str = "gpt-4.1",
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
        response = client.generate(
            model="gpt-4.1",
            prompt="Respond with a single word: Working",
            options={"temperature": 0.0}
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
