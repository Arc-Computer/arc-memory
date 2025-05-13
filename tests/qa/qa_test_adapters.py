#!/usr/bin/env python
"""
QA Test Script for Arc Memory SDK Framework Adapters.

This script tests the framework adapters of the Arc Memory SDK.
It verifies that the adapters can be initialized, functions can be adapted,
and agents can be created and used.

Usage:
    python qa_test_adapters.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Import Arc Memory SDK
try:
    from arc_memory import Arc
    from arc_memory.sdk.adapters import get_adapter, get_adapter_names
    from arc_memory.sdk.errors import FrameworkError
except ImportError as e:
    print(f"❌ Failed to import Arc Memory SDK: {e}")
    print("Please install Arc Memory SDK first: pip install arc-memory[all]")
    sys.exit(1)

# Initialize Arc
try:
    repo_path = Path.cwd()
    arc = Arc(repo_path=repo_path)
    print(f"✅ Successfully initialized Arc with repository path: {repo_path}")
except Exception as e:
    print(f"❌ Failed to initialize Arc: {e}")
    sys.exit(1)

# Test 1: Check available adapters
print("\nTest 1: Checking available adapters...")
try:
    adapter_names = get_adapter_names()
    print(f"✅ Available adapters: {', '.join(adapter_names)}")
except Exception as e:
    print(f"❌ Failed to get adapter names: {e}")
    sys.exit(1)

# Test 2: Test LangChain adapter
print("\nTest 2: Testing LangChain adapter...")
try:
    if "langchain" in adapter_names:
        # Get the LangChain adapter
        langchain_adapter = get_adapter("langchain")
        print(f"✅ Successfully got LangChain adapter: {langchain_adapter.get_name()}")

        # Adapt functions
        functions = [
            arc.query,
            arc.get_decision_trail,
            arc.get_related_entities,
            arc.get_entity_details,
            arc.analyze_component_impact
        ]

        tools = langchain_adapter.adapt_functions(functions)
        print(f"✅ Successfully adapted {len(tools)} functions to LangChain tools")

        # Check if we can create an agent
        try:
            # Check if LangChain is installed
            try:
                from langchain_openai import ChatOpenAI
                langchain_installed = True
            except ImportError:
                langchain_installed = False
                print("⚠️ LangChain not installed, skipping agent creation")

            if langchain_installed:
                # Check if OPENAI_API_KEY is set
                if "OPENAI_API_KEY" in os.environ:
                    # Create a LangChain agent
                    llm = ChatOpenAI(model="gpt-3.5-turbo")
                    agent = langchain_adapter.create_agent(
                        tools=tools,
                        llm=llm,
                        system_message="You are a helpful assistant with access to Arc Memory."
                    )
                    print("✅ Successfully created LangChain agent")

                    # Test the agent with a simple query
                    try:
                        response = agent.invoke({"input": "What can you tell me about this repository?"})
                        print("✅ Successfully invoked LangChain agent")
                        print(f"Response: {str(response)[:100]}...")
                    except Exception as e:
                        print(f"⚠️ Failed to invoke LangChain agent: {e}")
                else:
                    print("⚠️ OPENAI_API_KEY not set, skipping agent creation")
        except Exception as e:
            print(f"⚠️ Failed to create LangChain agent: {e}")
    else:
        print("⚠️ LangChain adapter not available")
except Exception as e:
    print(f"❌ Failed to test LangChain adapter: {e}")

# Test 3: Test OpenAI adapter
print("\nTest 3: Testing OpenAI adapter...")
try:
    if "openai" in adapter_names:
        # Get the OpenAI adapter
        openai_adapter = get_adapter("openai")
        print(f"✅ Successfully got OpenAI adapter: {openai_adapter.get_name()}")

        # Adapt functions
        functions = [
            arc.query,
            arc.get_decision_trail,
            arc.get_related_entities,
            arc.get_entity_details,
            arc.analyze_component_impact
        ]

        tools = openai_adapter.adapt_functions(functions)
        print(f"✅ Successfully adapted {len(tools)} functions to OpenAI tools")

        # Check if we can create an agent
        try:
            # Check if OpenAI is installed
            try:
                import openai
                openai_installed = True
            except ImportError:
                openai_installed = False
                print("⚠️ OpenAI not installed, skipping agent creation")

            if openai_installed:
                # Check if OPENAI_API_KEY is set
                if "OPENAI_API_KEY" in os.environ:
                    # Create an OpenAI agent
                    agent = openai_adapter.create_agent(
                        tools=tools,
                        model="gpt-3.5-turbo",
                        system_message="You are a helpful assistant with access to Arc Memory."
                    )
                    print("✅ Successfully created OpenAI agent")

                    # Test the agent with a simple query
                    try:
                        response = agent("What can you tell me about this repository?")
                        print("✅ Successfully invoked OpenAI agent")

                        # Check if the response contains content or tool calls
                        message = response.choices[0].message
                        if message.content:
                            print(f"Response content: {str(message.content)[:100]}...")
                        elif hasattr(message, 'tool_calls') and message.tool_calls:
                            tool_calls = message.tool_calls
                            print(f"Response contains {len(tool_calls)} tool call(s)")
                            for i, tool_call in enumerate(tool_calls):
                                print(f"  Tool call {i+1}: {tool_call.function.name}")
                        else:
                            print("Response contains no content or tool calls")
                    except Exception as e:
                        print(f"⚠️ Failed to invoke OpenAI agent: {e}")
                else:
                    print("⚠️ OPENAI_API_KEY not set, skipping agent creation")
        except Exception as e:
            print(f"⚠️ Failed to create OpenAI agent: {e}")
    else:
        print("⚠️ OpenAI adapter not available")
except Exception as e:
    print(f"❌ Failed to test OpenAI adapter: {e}")

# Test 4: Test custom adapter registration
print("\nTest 4: Testing custom adapter registration...")
try:
    from arc_memory.sdk.adapters import register_adapter
    from arc_memory.sdk.adapters.base import FrameworkAdapter

    # Define a simple custom adapter
    class CustomAdapter:
        def get_name(self) -> str:
            return "custom"

        def get_supported_versions(self) -> List[str]:
            return ["0.1.0"]

        def adapt_functions(self, functions: List) -> List:
            return [{"name": func.__name__, "description": func.__doc__} for func in functions]

        def create_agent(self, **kwargs):
            return lambda query: f"Custom agent response to: {query}"

    # Register the custom adapter
    try:
        register_adapter(CustomAdapter())
        print("✅ Successfully registered custom adapter")

        # Get the custom adapter
        custom_adapter = get_adapter("custom")
        print(f"✅ Successfully got custom adapter: {custom_adapter.get_name()}")

        # Adapt functions
        functions = [arc.query]
        tools = custom_adapter.adapt_functions(functions)
        print(f"✅ Successfully adapted {len(tools)} functions to custom tools")

        # Create a custom agent
        agent = custom_adapter.create_agent()
        print("✅ Successfully created custom agent")

        # Test the agent
        response = agent("Test query")
        print(f"✅ Custom agent response: {response}")
    except Exception as e:
        print(f"❌ Failed to register or use custom adapter: {e}")
except Exception as e:
    print(f"❌ Failed to test custom adapter registration: {e}")

# Test 5: Test error handling
print("\nTest 5: Testing error handling...")
try:
    # Try to get a non-existent adapter
    try:
        non_existent_adapter = get_adapter("non_existent")
        print("❌ Got non-existent adapter (should have failed)")
    except FrameworkError as e:
        print(f"✅ Correctly handled non-existent adapter: {e}")

    # Try to create an agent with invalid parameters
    if "openai" in adapter_names:
        openai_adapter = get_adapter("openai")
        try:
            # Invalid model name
            agent = openai_adapter.create_agent(
                tools=[],
                model="non_existent_model",
                system_message="Test"
            )
            print("❌ Created agent with invalid model (should have failed)")
        except FrameworkError as e:
            print(f"✅ Correctly handled invalid model: {e}")
except Exception as e:
    print(f"❌ Failed to test error handling: {e}")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory SDK framework adapters tests completed.")
print("Run 'python qa_test_cli.py' to test CLI commands.")
