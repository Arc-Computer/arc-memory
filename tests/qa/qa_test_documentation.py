#!/usr/bin/env python
"""
QA Test Script for Arc Memory Documentation Consistency.

This script tests the consistency of the Arc Memory documentation.
It verifies that the examples in the documentation match the actual API,
and that the parameter names and descriptions are consistent.

Usage:
    python qa_test_documentation.py
"""

import os
import sys
import re
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Set

# Import Arc Memory SDK
try:
    from arc_memory import Arc
    from arc_memory.sdk.adapters import get_adapter, get_adapter_names
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

# Test 1: Check API methods against documentation
print("\nTest 1: Checking API methods against documentation...")

# Get actual methods from Arc class
arc_methods = [name for name, func in inspect.getmembers(arc, inspect.ismethod)
               if not name.startswith('_')]
print(f"✅ Found {len(arc_methods)} methods in Arc class")
print(f"   Methods: {', '.join(arc_methods)}")

# Read API reference documentation
api_reference_path = Path("docs/sdk/api_reference.md")
if api_reference_path.exists():
    api_reference_content = api_reference_path.read_text()
    
    # Extract method names from documentation using regex
    method_pattern = r"def\s+(\w+)\s*\("
    doc_methods = re.findall(method_pattern, api_reference_content)
    
    print(f"✅ Found {len(doc_methods)} methods in API reference documentation")
    print(f"   Methods: {', '.join(doc_methods)}")
    
    # Check for methods in code but not in docs
    missing_in_docs = set(arc_methods) - set(doc_methods)
    if missing_in_docs:
        print(f"⚠️ Methods in code but not in docs: {', '.join(missing_in_docs)}")
    else:
        print("✅ All methods in code are documented")
    
    # Check for methods in docs but not in code
    missing_in_code = set(doc_methods) - set(arc_methods)
    if missing_in_code:
        print(f"⚠️ Methods in docs but not in code: {', '.join(missing_in_code)}")
    else:
        print("✅ All documented methods exist in code")
else:
    print(f"⚠️ API reference documentation not found at {api_reference_path}")

# Test 2: Check parameter consistency
print("\nTest 2: Checking parameter consistency...")

# Get parameters for key methods
key_methods = ['query', 'get_decision_trail', 'get_related_entities', 'analyze_component_impact', 'export_graph']
method_params = {}

for method_name in key_methods:
    if hasattr(arc, method_name):
        method = getattr(arc, method_name)
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        method_params[method_name] = params
        print(f"✅ Method '{method_name}' has parameters: {', '.join(params)}")
    else:
        print(f"⚠️ Method '{method_name}' not found in Arc class")

# Check parameter consistency in documentation
if api_reference_path.exists():
    for method_name, params in method_params.items():
        # Extract parameter section for this method from documentation
        method_pattern = rf"def\s+{method_name}\s*\(([^)]*)\)"
        param_matches = re.search(method_pattern, api_reference_content)
        
        if param_matches:
            doc_params_str = param_matches.group(1)
            doc_params = [p.strip().split(':')[0].strip() for p in doc_params_str.split(',')]
            doc_params = [p for p in doc_params if p and p != 'self']
            
            # Check for parameters in code but not in docs
            missing_in_docs = set(params) - set(doc_params)
            if missing_in_docs:
                print(f"⚠️ Parameters for '{method_name}' in code but not in docs: {', '.join(missing_in_docs)}")
            else:
                print(f"✅ All parameters for '{method_name}' in code are documented")
            
            # Check for parameters in docs but not in code
            missing_in_code = set(doc_params) - set(params)
            if missing_in_code:
                print(f"⚠️ Parameters for '{method_name}' in docs but not in code: {', '.join(missing_in_code)}")
            else:
                print(f"✅ All documented parameters for '{method_name}' exist in code")
        else:
            print(f"⚠️ Could not find parameter section for '{method_name}' in documentation")

# Test 3: Check README examples
print("\nTest 3: Checking README examples...")

readme_path = Path("README.md")
if readme_path.exists():
    readme_content = readme_path.read_text()
    
    # Extract Python code blocks
    code_blocks = re.findall(r"```python\n(.*?)```", readme_content, re.DOTALL)
    print(f"✅ Found {len(code_blocks)} Python code blocks in README")
    
    # Check for common issues in code examples
    issues_found = False
    for i, block in enumerate(code_blocks):
        # Check for import statements
        if "import" in block and "arc_memory" not in block and "Arc" in block:
            print(f"⚠️ Code block {i+1} uses Arc but doesn't import from arc_memory")
            issues_found = True
        
        # Check for method calls that don't exist
        for line in block.split('\n'):
            if "arc." in line:
                method_match = re.search(r"arc\.(\w+)\(", line)
                if method_match:
                    method_name = method_match.group(1)
                    if method_name not in arc_methods and method_name != "get_adapter":
                        print(f"⚠️ Code block {i+1} calls non-existent method 'arc.{method_name}'")
                        issues_found = True
    
    if not issues_found:
        print("✅ No issues found in README code examples")
else:
    print(f"⚠️ README not found at {readme_path}")

# Test 4: Check quickstart guide
print("\nTest 4: Checking quickstart guide...")

quickstart_path = Path("docs/quickstart.md")
if quickstart_path.exists():
    quickstart_content = quickstart_path.read_text()
    
    # Extract Python code blocks
    code_blocks = re.findall(r"```python\n(.*?)```", quickstart_content, re.DOTALL)
    print(f"✅ Found {len(code_blocks)} Python code blocks in quickstart guide")
    
    # Check for common issues in code examples
    issues_found = False
    for i, block in enumerate(code_blocks):
        # Check for import statements
        if "import" in block and "arc_memory" not in block and "Arc" in block:
            print(f"⚠️ Code block {i+1} uses Arc but doesn't import from arc_memory")
            issues_found = True
        
        # Check for method calls that don't exist
        for line in block.split('\n'):
            if "arc." in line:
                method_match = re.search(r"arc\.(\w+)\(", line)
                if method_match:
                    method_name = method_match.group(1)
                    if method_name not in arc_methods and method_name != "get_adapter":
                        print(f"⚠️ Code block {i+1} calls non-existent method 'arc.{method_name}'")
                        issues_found = True
    
    if not issues_found:
        print("✅ No issues found in quickstart guide code examples")
else:
    print(f"⚠️ Quickstart guide not found at {quickstart_path}")

# Test 5: Check framework adapters documentation
print("\nTest 5: Checking framework adapters documentation...")

adapters_path = Path("docs/sdk/adapters.md")
if adapters_path.exists():
    adapters_content = adapters_path.read_text()
    
    # Extract adapter names from documentation
    adapter_pattern = r"get_adapter\([\"'](\w+)[\"']\)"
    doc_adapters = set(re.findall(adapter_pattern, adapters_content))
    
    # Get actual adapter names
    actual_adapters = set(get_adapter_names())
    
    print(f"✅ Found {len(doc_adapters)} adapters in documentation: {', '.join(doc_adapters)}")
    print(f"✅ Found {len(actual_adapters)} adapters in code: {', '.join(actual_adapters)}")
    
    # Check for adapters in code but not in docs
    missing_in_docs = actual_adapters - doc_adapters
    if missing_in_docs:
        print(f"⚠️ Adapters in code but not in docs: {', '.join(missing_in_docs)}")
    else:
        print("✅ All adapters in code are documented")
    
    # Check for adapters in docs but not in code
    missing_in_code = doc_adapters - actual_adapters
    if missing_in_code:
        print(f"⚠️ Adapters in docs but not in code: {', '.join(missing_in_code)}")
    else:
        print("✅ All documented adapters exist in code")
else:
    print(f"⚠️ Framework adapters documentation not found at {adapters_path}")

# Summary
print("\n=== Test Summary ===")
print("Arc Memory documentation consistency tests completed.")
print("Check the warnings above for potential documentation issues.")
