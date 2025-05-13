"""OpenAI adapter for Arc Memory SDK.

This module provides an adapter for integrating Arc Memory with OpenAI,
allowing Arc Memory functions to be used with OpenAI tool calling.
"""

import inspect
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from arc_memory.logging_conf import get_logger
from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.errors import FrameworkError

logger = get_logger(__name__)


class OpenAIAdapter(FrameworkAdapter):
    """Adapter for integrating Arc Memory with OpenAI.

    This adapter converts Arc Memory functions to OpenAI tool definitions,
    allowing them to be used with OpenAI tool calling.
    """

    def get_name(self) -> str:
        """Return a unique name for this adapter.

        Returns:
            A string identifier for this adapter.
        """
        return "openai"

    def get_supported_versions(self) -> List[str]:
        """Return a list of supported OpenAI versions.

        Returns:
            A list of supported version strings.
        """
        return ["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0"]

    def adapt_functions(self, functions: List[Callable]) -> List[Dict[str, Any]]:
        """Adapt Arc Memory functions to OpenAI tool definitions.

        Args:
            functions: List of Arc Memory functions to adapt.

        Returns:
            A list of OpenAI tool definitions.
        """
        openai_tools = []
        for func in functions:
            # Get the function signature
            sig = inspect.signature(func)

            # Get the function name and docstring
            name = func.__name__
            description = func.__doc__ or f"Call the {name} function"

            # Create the parameters schema
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }

            # Add parameters to the schema
            for param_name, param in sig.parameters.items():
                # Skip 'self' parameter
                if param_name == "self":
                    continue

                # Skip callback parameter
                if param_name == "callback":
                    continue

                # Determine parameter type
                param_type = param.annotation
                if param_type is inspect.Parameter.empty:
                    param_schema = {"type": "string"}
                elif param_type is str:
                    param_schema = {"type": "string"}
                elif param_type is int:
                    param_schema = {"type": "integer"}
                elif param_type is float:
                    param_schema = {"type": "number"}
                elif param_type is bool:
                    param_schema = {"type": "boolean"}
                elif param_type is List[str]:
                    param_schema = {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                elif param_type is List[int]:
                    param_schema = {
                        "type": "array",
                        "items": {"type": "integer"}
                    }
                else:
                    param_schema = {"type": "string"}

                # Add parameter to properties
                parameters["properties"][param_name] = param_schema

                # Add to required if no default value
                if param.default is inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            # Create tool definition
            tool_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
            openai_tools.append(tool_def)

        return openai_tools

    def create_agent(self, **kwargs) -> Any:
        """Create an OpenAI agent with Arc Memory functions.

        Args:
            **kwargs: Additional parameters for creating the agent.
                - tools: List of OpenAI tool definitions (required)
                - model: OpenAI model to use (optional)
                - temperature: Temperature for sampling (optional)
                - system_message: System message to use (optional)
                - stream: Whether to stream the response (optional)
                - stream_options: Options for streaming (optional)

        Returns:
            A callable that can be used to interact with the OpenAI API.

        Raises:
            ImportError: If OpenAI is not installed.
            ValueError: If required parameters are missing.
            FrameworkError: If there's an issue with the OpenAI API.
        """
        try:
            from openai import OpenAI
            from openai.types.chat import ChatCompletion
            from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
        except ImportError:
            raise ImportError(
                "OpenAI is not installed. Please install it with: "
                "pip install openai>=1.0.0"
            )

        # Get the tools from kwargs
        tools = kwargs.get("tools")
        if not tools:
            raise ValueError("tools parameter is required")

        # Get the model from kwargs or use a default
        model = kwargs.get("model", "gpt-4o")

        # Get the temperature from kwargs or use a default
        temperature = kwargs.get("temperature", 0)

        # Get the system message from kwargs or use a default
        system_message = kwargs.get("system_message", "You are a helpful assistant.")

        # Get streaming options
        stream = kwargs.get("stream", False)
        stream_options = kwargs.get("stream_options", None)

        # Create the OpenAI client
        client = OpenAI()

        # Create a callable that can be used to interact with the OpenAI API
        def agent(query: Union[str, List[Dict[str, str]]]) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
            """Call the OpenAI API with the given query.

            Args:
                query: The query to send to the OpenAI API. Can be a string or a list of messages.

            Returns:
                The response from the OpenAI API. If stream=True, returns an iterator of response chunks.

            Raises:
                FrameworkError: If there's an issue with the OpenAI API.
            """
            # Convert query to messages if it's a string
            if isinstance(query, str):
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ]
            else:
                # Assume it's already a list of messages
                messages = query
                # Add system message if not present
                if not any(msg.get("role") == "system" for msg in messages):
                    messages.insert(0, {"role": "system", "content": system_message})

            try:
                # Call the OpenAI API
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=temperature,
                    stream=stream,
                    stream_options=stream_options
                )

                return response
            except Exception as e:
                from arc_memory.sdk.errors import FrameworkError
                raise FrameworkError(
                    what_happened="Failed to call OpenAI API",
                    why_it_happened=f"OpenAI API returned an error: {str(e)}",
                    how_to_fix_it="Check your API key, model name, and request parameters. Ensure you have proper permissions and sufficient quota.",
                    details={"model": model, "error": str(e)}
                ) from e

        return agent

    def create_assistant(self, **kwargs) -> Any:
        """Create an OpenAI Assistant with Arc Memory functions.

        This method creates an OpenAI Assistant that can use Arc Memory functions
        as tools.

        Args:
            **kwargs: Additional parameters for creating the assistant.
                - tools: List of OpenAI tool definitions (required)
                - name: Name of the assistant (optional)
                - instructions: Instructions for the assistant (optional)
                - model: OpenAI model to use (optional)
                - metadata: Additional metadata for the assistant (optional)
                - description: Description of the assistant (optional)

        Returns:
            An OpenAI Assistant object.

        Raises:
            ImportError: If OpenAI is not installed.
            ValueError: If required parameters are missing.
            FrameworkError: If there's an issue with the OpenAI API.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI is not installed. Please install it with: "
                "pip install openai>=1.0.0"
            )

        # Get the tools from kwargs
        tools = kwargs.get("tools")
        if not tools:
            raise ValueError("tools parameter is required")

        # Get other parameters
        name = kwargs.get("name", "Arc Memory Assistant")
        instructions = kwargs.get("instructions", "You are a helpful assistant with access to Arc Memory.")
        model = kwargs.get("model", "gpt-4o")
        metadata = kwargs.get("metadata", None)
        description = kwargs.get("description", None)

        # Create the OpenAI client
        client = OpenAI()

        try:
            # Create the assistant
            assistant = client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model,
                tools=tools,
                metadata=metadata,
                description=description
            )

            return assistant
        except Exception as e:
            raise FrameworkError(
                what_happened="Failed to create OpenAI Assistant",
                why_it_happened=f"OpenAI API returned an error: {str(e)}",
                how_to_fix_it="Check your API key, model name, and request parameters. Ensure you have proper permissions and sufficient quota.",
                details={"model": model, "error": str(e)}
            ) from e
