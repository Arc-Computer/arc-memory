"""LangChain adapter for Arc Memory SDK.

This module provides an adapter for integrating Arc Memory with LangChain,
allowing Arc Memory functions to be used as LangChain tools.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from arc_memory.logging_conf import get_logger
from arc_memory.sdk.adapters.base import FrameworkAdapter

logger = get_logger(__name__)


class LangChainAdapter(FrameworkAdapter):
    """Adapter for integrating Arc Memory with LangChain.

    This adapter converts Arc Memory functions to LangChain tools,
    allowing them to be used in LangChain agents.
    """

    def get_name(self) -> str:
        """Return a unique name for this adapter.

        Returns:
            A string identifier for this adapter.
        """
        return "langchain"

    def get_supported_versions(self) -> List[str]:
        """Return a list of supported LangChain versions.

        Returns:
            A list of supported version strings.
        """
        return ["0.0.267", "0.0.268", "0.0.269", "0.0.270", "0.1.0", "0.2.0", "0.3.0"]

    def adapt_functions(self, functions: List[Callable]) -> List[Any]:
        """Adapt Arc Memory functions to LangChain tools.

        Args:
            functions: List of Arc Memory functions to adapt.

        Returns:
            A list of LangChain Tool objects.

        Raises:
            ImportError: If LangChain is not installed.
        """
        try:
            # Try importing from the new location first
            try:
                from langchain_core.tools import Tool
            except ImportError:
                # Fall back to the old location
                from langchain.tools import Tool
        except ImportError:
            raise ImportError(
                "LangChain is not installed. Please install it with: "
                "pip install langchain-core"
            )

        tools = []
        for func in functions:
            # Get the function name and docstring
            name = func.__name__
            description = func.__doc__ or f"Call the {name} function"

            # Create a LangChain tool
            tool = Tool(
                name=name,
                func=func,
                description=description
            )
            tools.append(tool)

        return tools

    def create_agent(self, **kwargs) -> Any:
        """Create a LangChain agent with Arc Memory tools.

        Args:
            **kwargs: Additional parameters for creating the agent.
                - tools: List of LangChain tools (required)
                - llm: LangChain language model (optional)
                - agent_type: Type of agent to create (optional)
                - verbose: Whether to enable verbose output (optional)
                - memory: Chat memory to use (optional)

        Returns:
            A LangChain agent.

        Raises:
            ImportError: If LangChain is not installed.
            ValueError: If required parameters are missing.
        """
        # Get the tools from kwargs
        tools = kwargs.get("tools")
        if not tools:
            raise ValueError("tools parameter is required")

        # Try to use LangGraph first (newer approach)
        try:
            # Remove tools from kwargs to avoid duplicate argument
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop("tools", None)
            return self._create_langgraph_agent(tools=tools, **kwargs_copy)
        except ImportError:
            logger.warning("LangGraph not installed, falling back to legacy AgentExecutor")
            # Remove tools from kwargs to avoid duplicate argument
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop("tools", None)
            return self._create_legacy_agent(tools=tools, **kwargs_copy)

    def _create_langgraph_agent(self, **kwargs) -> Any:
        """Create a LangGraph agent with Arc Memory tools.

        Args:
            **kwargs: Additional parameters for creating the agent.
                - tools: List of LangChain tools (required)
                - llm: LangChain language model (optional)
                - system_message: System message to use (optional)
                - memory: Chat memory to use (optional)

        Returns:
            A LangGraph agent.

        Raises:
            ImportError: If LangGraph is not installed.
        """
        try:
            from langgraph.prebuilt import create_react_agent
            from langchain_core.language_models import BaseLanguageModel
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "LangGraph is not installed. Please install it with: "
                "pip install langgraph langchain-core langchain-openai"
            )

        # Get the tools from kwargs
        tools = kwargs.get("tools")

        # Get the LLM from kwargs or use a default
        llm = kwargs.get("llm", ChatOpenAI(temperature=0))

        # Get the system message from kwargs or use a default
        system_message = kwargs.get("system_message", "You are a helpful assistant.")

        # Get the memory from kwargs
        memory = kwargs.get("memory")

        # Create the agent
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=system_message,
            checkpointer=memory
        )

        return agent

    def _create_legacy_agent(self, **kwargs) -> Any:
        """Create a legacy LangChain agent with Arc Memory tools.

        Args:
            **kwargs: Additional parameters for creating the agent.
                - tools: List of LangChain tools (required)
                - llm: LangChain language model (optional)
                - agent_type: Type of agent to create (optional)
                - verbose: Whether to enable verbose output (optional)
                - memory: Chat memory to use (optional)

        Returns:
            A LangChain AgentExecutor.

        Raises:
            ImportError: If LangChain is not installed.
        """
        try:
            # Try importing from the new location first
            try:
                from langchain.agents import AgentExecutor, create_tool_calling_agent
                from langchain_core.language_models import BaseLanguageModel
                from langchain_openai import ChatOpenAI
            except ImportError:
                # Fall back to the old location
                from langchain.agents import AgentExecutor, initialize_agent, AgentType
                from langchain.llms import OpenAI
        except ImportError:
            raise ImportError(
                "LangChain is not installed. Please install it with: "
                "pip install langchain langchain-openai"
            )

        # Get the tools from kwargs
        tools = kwargs.get("tools")

        # Get the LLM from kwargs or use a default
        llm = kwargs.get("llm")
        if not llm:
            try:
                llm = ChatOpenAI(temperature=0)
            except NameError:
                llm = OpenAI(temperature=0)

        # Get the memory from kwargs
        memory = kwargs.get("memory")

        # Create the agent
        try:
            # Try the newer approach first
            agent = create_tool_calling_agent(llm, tools)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=kwargs.get("verbose", True)
            )
        except (NameError, AttributeError):
            # Fall back to the older approach
            agent_type = kwargs.get("agent_type", AgentType.ZERO_SHOT_REACT_DESCRIPTION)
            agent_executor = initialize_agent(
                tools=tools,
                llm=llm,
                agent=agent_type,
                memory=memory,
                verbose=kwargs.get("verbose", True)
            )

        return agent_executor
