"""Model wrapper utilities for Arc Memory simulation.

This module provides model wrappers for different LLM providers to be used
with Smol Agents in the Arc Memory simulation workflow.
"""

import os
from typing import List, Dict, Any, Union, Optional

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


def create_openai_wrapper(api_key: Optional[str] = None, model_id: str = "gpt-4o"):
    """Create an OpenAI model wrapper for use with Smol Agents.
    
    Args:
        api_key: OpenAI API key (optional, will use environment variable if not provided)
        model_id: Model ID to use (default: "gpt-4o")
        
    Returns:
        OpenAIModelWrapper instance
        
    Raises:
        ImportError: If OpenAI or Smol Agents are not installed
        RuntimeError: If API key is not provided and not found in environment
    """
    # Import OpenAI
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("OpenAI is not installed. Please install it with 'pip install openai'.")
        raise ImportError("OpenAI is not installed. Please install it with 'pip install openai'.")
    
    # Import Smol Agents
    try:
        from smolagents.models import ChatMessage
    except ImportError:
        logger.error("Smol Agents is not installed. Please install it with 'pip install smolagents'.")
        raise ImportError("Smol Agents is not installed. Please install it with 'pip install smolagents'.")
    
    # Import environment utilities
    from arc_memory.simulate.utils.env import get_api_key
    
    # Get the API key from the environment or provided value
    api_key = get_api_key(api_key, "OPENAI_API_KEY")
    
    # Create a client with the API key
    openai_client = OpenAI(api_key=api_key)
    
    # Create a wrapper for the OpenAI client that matches the LiteLLMModel interface
    class OpenAIModelWrapper:
        def __init__(self, client, model_id, temperature=0.1, max_tokens=4000):
            self.client = client
            self.model_id = model_id
            self.temperature = temperature
            self.max_tokens = max_tokens
        
        def __call__(self, messages, **kwargs):
            # Convert messages to the format expected by OpenAI
            formatted_messages = []
            for message in messages:
                if isinstance(message["content"], list):
                    # Handle multi-modal content
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
                else:
                    # Handle text-only content
                    formatted_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=formatted_messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens)
            )
            
            # Return a response object that matches the LiteLLMModel interface
            return ChatMessage(
                role="assistant",
                content=response.choices[0].message.content
            )
    
    # Return an instance of the wrapper
    return OpenAIModelWrapper(openai_client, model_id)
