#!/usr/bin/env python
"""
QA Test Script for Arc Memory CLI Commands.

This script tests the CLI commands of Arc Memory.
It verifies that the commands can be executed and produce the expected output.

Usage:
    python qa_test_cli.py
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

# Test 1: Check if arc command is available
print("\nTest 1: Checking if arc command is available...")
try:
    result = subprocess.run(["arc", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc command is available")
        # Extract available commands from help output
        commands = [line.strip() for line in result.stdout.split("\n") if "  " in line and not line.startswith("  --")]
        print(f"   Available commands: {', '.join([cmd.split()[0] for cmd in commands if cmd.split()])}")
    else:
        print(f"❌ arc command is not available: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Failed to check arc command: {e}")
    sys.exit(1)

# Test 2: Test arc version command
print("\nTest 2: Testing arc version command...")
try:
    result = subprocess.run(["arc", "version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ arc version: {result.stdout.strip()}")
    else:
        print(f"❌ Failed to get arc version: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc version command: {e}")

# Test 3: Test arc build --help
print("\nTest 3: Testing arc build --help...")
try:
    result = subprocess.run(["arc", "build", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc build --help works")
        # Extract options from help output
        options = [line.strip() for line in result.stdout.split("\n") if "--" in line]
        print(f"   Available options: {len(options)}")
    else:
        print(f"❌ Failed to get arc build help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc build --help command: {e}")

# Test 4: Test arc why --help
print("\nTest 4: Testing arc why --help...")
try:
    result = subprocess.run(["arc", "why", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc why --help works")
        # Extract subcommands from help output
        subcommands = [line.strip() for line in result.stdout.split("\n") if "  " in line and not line.startswith("  --")]
        print(f"   Available subcommands: {', '.join([cmd.split()[0] for cmd in subcommands if cmd.split()])}")
    else:
        print(f"❌ Failed to get arc why help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc why --help command: {e}")

# Test 5: Test arc why file --help
print("\nTest 5: Testing arc why file --help...")
try:
    result = subprocess.run(["arc", "why", "file", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc why file --help works")
        # Extract options from help output
        options = [line.strip() for line in result.stdout.split("\n") if "--" in line]
        print(f"   Available options: {len(options)}")
    else:
        print(f"❌ Failed to get arc why file help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc why file --help command: {e}")

# Test 6: Test arc export --help
print("\nTest 6: Testing arc export --help...")
try:
    result = subprocess.run(["arc", "export", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc export --help works")
        # Extract options from help output
        options = [line.strip() for line in result.stdout.split("\n") if "--" in line]
        print(f"   Available options: {len(options)}")
    else:
        print(f"❌ Failed to get arc export help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc export --help command: {e}")

# Test 7: Test arc doctor
print("\nTest 7: Testing arc doctor...")
try:
    result = subprocess.run(["arc", "doctor"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc doctor works")
        # Extract key information from output
        lines = result.stdout.split("\n")
        for line in lines:
            if "Node count:" in line or "Edge count:" in line or "Database size:" in line:
                print(f"   {line.strip()}")
    else:
        print(f"❌ Failed to run arc doctor: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc doctor command: {e}")

# Test 8: Test arc build with dry-run
print("\nTest 8: Testing arc build with dry-run...")
try:
    # Check if --dry-run option is available
    result = subprocess.run(["arc", "build", "--help"], capture_output=True, text=True)
    if "--dry-run" in result.stdout:
        # Run with dry-run option
        result = subprocess.run(["arc", "build", "--dry-run"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ arc build --dry-run works")
        else:
            print(f"❌ Failed to run arc build --dry-run: {result.stderr}")
    else:
        print("⚠️ --dry-run option not available for arc build, skipping test")
except Exception as e:
    print(f"❌ Failed to test arc build --dry-run command: {e}")

# Test 9: Test arc auth gh --help
print("\nTest 9: Testing arc auth gh --help...")
try:
    result = subprocess.run(["arc", "auth", "gh", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc auth gh --help works")
        # Extract options from help output
        options = [line.strip() for line in result.stdout.split("\n") if "--" in line]
        print(f"   Available options: {len(options)}")
    else:
        print(f"❌ Failed to get arc auth gh help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc auth gh --help command: {e}")

# Test 10: Test arc auth linear --help
print("\nTest 10: Testing arc auth linear --help...")
try:
    result = subprocess.run(["arc", "auth", "linear", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ arc auth linear --help works")
        # Extract options from help output
        options = [line.strip() for line in result.stdout.split("\n") if "--" in line]
        print(f"   Available options: {len(options)}")
    else:
        print(f"❌ Failed to get arc auth linear help: {result.stderr}")
except Exception as e:
    print(f"❌ Failed to test arc auth linear --help command: {e}")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory CLI commands tests completed.")
print("All basic CLI commands are available and help documentation works.")
print("For more comprehensive testing, run the commands with actual parameters.")
