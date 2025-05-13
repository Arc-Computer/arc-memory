#!/usr/bin/env python
"""
QA Test Script for Arc Memory Ollama Dependency.

This script tests the Ollama dependency of Arc Memory.
It verifies whether Ollama is installed and running,
and tests natural language queries with and without Ollama.

Usage:
    python qa_test_ollama.py
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using existing environment variables")

# Import Arc Memory SDK
try:
    from arc_memory import Arc
except ImportError as e:
    print(f"❌ Failed to import Arc Memory SDK: {e}")
    print("Please install Arc Memory SDK first: pip install arc-memory[all]")
    sys.exit(1)

# Test 1: Check if Ollama is installed
print("\nTest 1: Checking if Ollama is installed...")
try:
    result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
    if result.returncode == 0:
        ollama_path = result.stdout.strip()
        print(f"✅ Ollama is installed at: {ollama_path}")
    else:
        print("❌ Ollama is not installed")
        print("Please install Ollama: https://ollama.ai/download")
except Exception as e:
    print(f"❌ Failed to check if Ollama is installed: {e}")

# Test 2: Check if Ollama is running
print("\nTest 2: Checking if Ollama is running...")
try:
    result = subprocess.run(["pgrep", "ollama"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Ollama is running")
    else:
        print("❌ Ollama is not running")
        print("Please start Ollama: ollama serve")
except Exception as e:
    print(f"❌ Failed to check if Ollama is running: {e}")

# Test 3: Check available Ollama models
print("\nTest 3: Checking available Ollama models...")
try:
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if result.returncode == 0:
        models = [line.split()[0] for line in result.stdout.strip().split("\n")[1:] if line.strip()]
        print(f"✅ Available Ollama models: {', '.join(models)}")
    else:
        print(f"❌ Failed to list Ollama models: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to check available Ollama models: {e}")

# Test 4: Initialize Arc
print("\nTest 4: Initializing Arc...")
try:
    repo_path = Path.cwd()
    arc = Arc(repo_path=repo_path)
    print(f"✅ Successfully initialized Arc with repository path: {repo_path}")
except Exception as e:
    print(f"❌ Failed to initialize Arc: {e}")
    sys.exit(1)

# Test 5: Check if graph exists
print("\nTest 5: Checking if graph exists...")
try:
    node_count = arc.get_node_count()
    print(f"✅ Graph exists with {node_count} nodes")
    
    if node_count == 0:
        print("⚠️ Graph is empty. Run 'arc build' to build the knowledge graph.")
        print("Skipping remaining tests that require a built graph.")
        sys.exit(0)
except Exception as e:
    print(f"❌ Failed to check if graph exists: {e}")
    sys.exit(1)

# Test 6: Test query functionality with Ollama
print("\nTest 6: Testing query functionality with Ollama...")
try:
    # Use a generic question that should work with any repository
    question = "What are the main components of this repository?"
    print(f"Querying: '{question}'")
    
    start_time = time.time()
    try:
        result = arc.query(question=question, max_results=3, max_hops=2, timeout=30)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Query completed in {elapsed_time:.2f} seconds")
        print(f"Answer: {result.answer[:100]}..." if len(result.answer) > 100 else f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence}")
        print(f"Evidence count: {len(result.evidence)}")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        print("This is likely due to Ollama not being installed or running.")
        print("Please install Ollama: https://ollama.ai/download")
        print("And start it: ollama serve")
except Exception as e:
    print(f"❌ Failed to test query functionality: {e}")

# Test 7: Check if query functionality works without Ollama
print("\nTest 7: Testing if query functionality works without Ollama...")
try:
    # Stop Ollama if it's running
    print("Stopping Ollama...")
    subprocess.run(["pkill", "ollama"], capture_output=True, text=True)
    time.sleep(2)
    
    # Check if Ollama is stopped
    result = subprocess.run(["pgrep", "ollama"], capture_output=True, text=True)
    if result.returncode != 0:
        print("✅ Ollama is stopped")
    else:
        print("⚠️ Failed to stop Ollama")
    
    # Try to query without Ollama
    question = "What are the main components of this repository?"
    print(f"Querying without Ollama: '{question}'")
    
    start_time = time.time()
    try:
        result = arc.query(question=question, max_results=3, max_hops=2, timeout=10)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Query completed without Ollama in {elapsed_time:.2f} seconds")
        print(f"Answer: {result.answer[:100]}..." if len(result.answer) > 100 else f"Answer: {result.answer}")
        print(f"Confidence: {result.confidence}")
        print(f"Evidence count: {len(result.evidence)}")
    except Exception as e:
        print(f"❌ Query failed without Ollama: {e}")
        print("This confirms that Ollama is required for natural language queries.")
except Exception as e:
    print(f"❌ Failed to test query functionality without Ollama: {e}")

# Test 8: Restart Ollama
print("\nTest 8: Restarting Ollama...")
try:
    print("Starting Ollama...")
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)
    
    # Check if Ollama is running
    result = subprocess.run(["pgrep", "ollama"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Ollama is restarted")
    else:
        print("⚠️ Failed to restart Ollama")
except Exception as e:
    print(f"❌ Failed to restart Ollama: {e}")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory Ollama dependency tests completed.")
print("Ollama is required for natural language queries.")
print("Please ensure Ollama is installed and running before using natural language queries.")
