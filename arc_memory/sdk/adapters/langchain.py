"""LangChain adapter for Arc Memory SDK.

This module provides an adapter for integrating Arc Memory with LangChain,
allowing Arc Memory functions to be used as LangChain tools.
"""

from typing import Any, Callable, Iterator, List

from arc_memory.logging_conf import get_logger
from arc_memory.sdk.adapters.base import FrameworkAdapter
from arc_memory.sdk.errors import FrameworkError

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
        return ["0.0.267", "0.0.268", "0.0.269", "0.0.270", "0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0"]

    def adapt_functions(self, functions: List[Callable]) -> List[Any]:
        """Adapt Arc Memory functions to LangChain tools.

        Args:
            functions: List of Arc Memory functions to adapt.

        Returns:
            A list of LangChain Tool objects.

        Raises:
            FrameworkError: If LangChain is not installed or there's an issue adapting the functions.
        """
        try:
            # Try importing from the new location first (LangChain v0.1.0+)
            try:
                from langchain_core.tools import Tool
            except ImportError:
                # Fall back to the old location (LangChain v0.0.x)
                try:
                    from langchain.tools import Tool
                except ImportError:
                    raise ImportError(
                        "LangChain is not installed. Please install it with: "
                        "pip install langchain-core>=0.1.0"
                    )
        except ImportError as e:
            raise FrameworkError(
                what_happened="Failed to import LangChain",
                why_it_happened=f"LangChain is not installed or incompatible: {str(e)}",
                how_to_fix_it="Install LangChain with: pip install langchain-core>=0.1.0 langchain-openai",
                details={"error": str(e)}
            ) from e

        tools = []
        try:
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
        except Exception as e:
            raise FrameworkError(
                what_happened="Failed to adapt functions to LangChain tools",
                why_it_happened=f"Error creating LangChain tools: {str(e)}",
                how_to_fix_it="Check that the functions have proper docstrings and signatures",
                details={"error": str(e), "functions": [f.__name__ for f in functions]}
            ) from e

    def create_agent(self, **kwargs) -> Any:
        """Create a LangChain agent with Arc Memory tools.

        Args:
            **kwargs: Additional parameters for creating the agent.
                - tools: List of LangChain tools (required)
                - llm: LangChain language model (optional)
                - agent_type: Type of agent to create (optional)
                - verbose: Whether to enable verbose output (optional)
                - memory: Chat memory to use (optional)
                - use_langgraph: Whether to use LangGraph (optional, default: auto-detect)

        Returns:
            A LangChain agent.

        Raises:
            FrameworkError: If there's an issue creating the agent.
            ValueError: If required parameters are missing.
        """
        # Get the tools from kwargs
        tools = kwargs.get("tools")
        if not tools:
            raise ValueError("tools parameter is required")

        # Check if user explicitly specified which agent type to use
        use_langgraph = kwargs.get("use_langgraph")

        try:
            # If use_langgraph is explicitly set to True, use LangGraph
            if use_langgraph is True:
                # Remove tools from kwargs to avoid duplicate argument
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop("tools", None)
                kwargs_copy.pop("use_langgraph", None)
                return self._create_langgraph_agent(tools=tools, **kwargs_copy)

            # If use_langgraph is explicitly set to False, use legacy AgentExecutor
            elif use_langgraph is False:
                # Remove tools from kwargs to avoid duplicate argument
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop("tools", None)
                kwargs_copy.pop("use_langgraph", None)
                return self._create_legacy_agent(tools=tools, **kwargs_copy)

            # Otherwise, try to use LangGraph first (newer approach)
            else:
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
        except Exception as e:
            raise FrameworkError(
                what_happened="Failed to create LangChain agent",
                why_it_happened=f"Error creating agent: {str(e)}",
                how_to_fix_it="Check that LangChain is installed and the parameters are correct",
                details={"error": str(e), "kwargs": str(kwargs)}
            ) from e

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
            FrameworkError: If LangGraph is not installed or there's an issue creating the agent.
        """
        try:
            try:
                # Try importing from langgraph.prebuilt (newer versions)
                from langgraph.prebuilt import create_react_agent
            except ImportError:
                # Try importing from langchain.agents.agent_types (older versions)
                try:
                    from langchain.agents.agent_types import create_react_agent
                except ImportError:
                    raise ImportError(
                        "LangGraph is not installed. Please install it with: "
                        "pip install langgraph langchain-core>=0.1.0 langchain-openai"
                    )

            # Import ChatOpenAI for default LLM
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise FrameworkError(
                what_happened="Failed to import LangGraph",
                why_it_happened=f"LangGraph is not installed or incompatible: {str(e)}",
                how_to_fix_it="Install LangGraph with: pip install langgraph langchain-core>=0.1.0 langchain-openai",
                details={"error": str(e)}
            ) from e

        try:
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
        except Exception as e:
            raise FrameworkError(
                what_happened="Failed to create LangGraph agent",
                why_it_happened=f"Error creating LangGraph agent: {str(e)}",
                how_to_fix_it="Check that LangGraph is installed and the parameters are correct",
                details={"error": str(e), "kwargs": str(kwargs)}
            ) from e

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
            FrameworkError: If LangChain is not installed or there's an issue creating the agent.
        """
        try:
            # Try importing from langchain_core first (v0.1.0+)
            try:
                from langchain_core.agents import AgentExecutor
                from langchain_core.tools import BaseTool
                from langchain_openai import ChatOpenAI

                # Check if we can import the newer tool calling agent
                try:
                    from langchain.agents import create_tool_calling_agent
                    has_tool_calling = True
                except ImportError:
                    has_tool_calling = False

                # Check if we need to fall back to older initialize_agent
                try:
                    from langchain.agents import initialize_agent, AgentType
                    has_initialize_agent = True
                except ImportError:
                    has_initialize_agent = False
            except ImportError:
                # Fall back to older imports (v0.0.x)
                try:
                    from langchain.agents import AgentExecutor, initialize_agent, AgentType
                    from langchain.llms import OpenAI
                    has_tool_calling = False
                    has_initialize_agent = True
                except ImportError:
                    raise ImportError(
                        "LangChain is not installed. Please install it with: "
                        "pip install langchain-core>=0.1.0 langchain-openai"
                    )
        except ImportError as e:
            raise FrameworkError(
                what_happened="Failed to import LangChain",
                why_it_happened=f"LangChain is not installed or incompatible: {str(e)}",
                how_to_fix_it="Install LangChain with: pip install langchain-core>=0.1.0 langchain-openai",
                details={"error": str(e)}
            ) from e

        try:
            # Get the tools from kwargs
            tools = kwargs.get("tools")

            # Get the LLM from kwargs or use a default
            llm = kwargs.get("llm")
            if not llm:
                try:
                    llm = ChatOpenAI(temperature=0)
                except (NameError, ImportError):
                    try:
                        llm = OpenAI(temperature=0)
                    except (NameError, ImportError):
                        raise FrameworkError(
                            what_happened="Failed to create default LLM",
                            why_it_happened="Neither ChatOpenAI nor OpenAI could be imported",
                            how_to_fix_it="Install langchain-openai or provide an LLM explicitly",
                            details={"error": "LLM import failed"}
                        )

            # Get the memory from kwargs
            memory = kwargs.get("memory")
            verbose = kwargs.get("verbose", True)

            # Create the agent
            if has_tool_calling:
                # Use the newer approach
                agent = create_tool_calling_agent(llm, tools)
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    memory=memory,
                    verbose=verbose
                )
            elif has_initialize_agent:
                # Use the older approach
                agent_type = kwargs.get("agent_type", AgentType.ZERO_SHOT_REACT_DESCRIPTION)
                agent_executor = initialize_agent(
                    tools=tools,
                    llm=llm,
                    agent=agent_type,
                    memory=memory,
                    verbose=verbose
                )
            else:
                raise FrameworkError(
                    what_happened="Failed to create LangChain agent",
                    why_it_happened="No compatible agent creation method found",
                    how_to_fix_it="Install a compatible version of LangChain",
                    details={"error": "No agent creation method available"}
                )

            return agent_executor
        except Exception as e:
            raise FrameworkError(
                what_happened="Failed to create LangChain agent",
                why_it_happened=f"Error creating agent: {str(e)}",
                how_to_fix_it="Check that LangChain is installed and the parameters are correct",
                details={"error": str(e), "kwargs": str(kwargs)}
            ) from e
