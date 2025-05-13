#!/usr/bin/env python
"""
QA Test Script for Arc Memory SDK Installation and Basic Functionality.

This script tests the installation and basic functionality of the Arc Memory SDK.
It verifies that the package can be imported, the Arc class can be initialized,
and basic operations can be performed.

Usage:
    python qa_test_installation.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Test 1: Import Arc Memory SDK
print("Test 1: Importing Arc Memory SDK...")
try:
    from arc_memory import Arc
    from arc_memory.sdk.adapters import get_adapter, get_adapter_names
    print("✅ Successfully imported Arc Memory SDK")
except ImportError as e:
    print(f"❌ Failed to import Arc Memory SDK: {e}")
    sys.exit(1)

# Test 2: Check SDK Version
print("\nTest 2: Checking SDK Version...")
try:
    import arc_memory
    print(f"✅ Arc Memory SDK version: {arc_memory.__version__}")
except Exception as e:
    print(f"❌ Failed to get SDK version: {e}")

# Test 3: Initialize Arc Class
print("\nTest 3: Initializing Arc Class...")
try:
    # Use current directory as repository path
    repo_path = Path.cwd()
    arc = Arc(repo_path=repo_path)
    print(f"✅ Successfully initialized Arc with repository path: {repo_path}")
except Exception as e:
    print(f"❌ Failed to initialize Arc: {e}")
    sys.exit(1)

# Test 4: Check Available Adapters
print("\nTest 4: Checking Available Adapters...")
try:
    adapter_names = get_adapter_names()
    print(f"✅ Available adapters: {', '.join(adapter_names)}")
except Exception as e:
    print(f"❌ Failed to get adapter names: {e}")

# Test 5: Test LangChain Adapter (if available)
print("\nTest 5: Testing LangChain Adapter...")
try:
    if "langchain" in get_adapter_names():
        langchain_adapter = get_adapter("langchain")
        print(f"✅ Successfully got LangChain adapter: {langchain_adapter.get_name()}")
        print(f"   Supported versions: {', '.join(langchain_adapter.get_supported_versions())}")
    else:
        print("⚠️ LangChain adapter not available")
except Exception as e:
    print(f"❌ Failed to get LangChain adapter: {e}")

# Test 6: Test OpenAI Adapter (if available)
print("\nTest 6: Testing OpenAI Adapter...")
try:
    if "openai" in get_adapter_names():
        openai_adapter = get_adapter("openai")
        print(f"✅ Successfully got OpenAI adapter: {openai_adapter.get_name()}")
        print(f"   Supported versions: {', '.join(openai_adapter.get_supported_versions())}")
    else:
        print("⚠️ OpenAI adapter not available")
except Exception as e:
    print(f"❌ Failed to get OpenAI adapter: {e}")

# Test 7: Check Database Connection
print("\nTest 7: Checking Database Connection...")
try:
    # Check if adapter is connected
    if arc.adapter.is_connected():
        print("✅ Successfully connected to database")
    else:
        print("❌ Not connected to database")
except Exception as e:
    print(f"❌ Failed to check database connection: {e}")

# Test 8: Test Basic Graph Operations (if database exists)
print("\nTest 8: Testing Basic Graph Operations...")
try:
    # Get node count
    node_count = arc.get_node_count()
    print(f"✅ Node count: {node_count}")
    
    # If graph is empty, print a message
    if node_count == 0:
        print("   Graph is empty. Run 'arc build' to build the knowledge graph.")
except Exception as e:
    print(f"❌ Failed to get node count: {e}")

# Test 9: Test CLI Command Availability
print("\nTest 9: Testing CLI Command Availability...")
try:
    import subprocess
    result = subprocess.run(["arc", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ CLI commands are available")
        # Extract available commands from help output
        commands = [line.strip() for line in result.stdout.split("\n") if "  " in line and not line.startswith("  --")]
        print(f"   Available commands: {', '.join([cmd.split()[0] for cmd in commands if cmd.split()])}")
    else:
        print(f"❌ CLI commands are not available: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test CLI commands: {e}")

# Test 10: Check Environment Variables
print("\nTest 10: Checking Environment Variables...")
env_vars = {
    "GITHUB_TOKEN": "GitHub authentication",
    "LINEAR_API_KEY": "Linear authentication",
    "OPENAI_API_KEY": "OpenAI integration",
}
for var, description in env_vars.items():
    if var in os.environ:
        # Mask the token for security
        token = os.environ[var]
        masked_token = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "***"
        print(f"✅ {var} is set ({description}): {masked_token}")
    else:
        print(f"⚠️ {var} is not set ({description})")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory SDK installation and basic functionality tests completed.")
print("Run 'python qa_test_functionality.py' to test core functionality.")
print("Run 'python qa_test_adapters.py' to test framework adapters.")
