#!/usr/bin/env python3
"""
Debug script to examine the raw LLM response for JavaScript/TypeScript analysis.
"""

import sys
from pathlib import Path
from arc_memory.ingest.code_analysis import CodeAnalysisIngestor
from arc_memory.llm.ollama_client import OllamaClient

def debug_js_analysis(file_path):
    """Debug the JavaScript/TypeScript file analysis."""
    print(f"Analyzing file: {file_path}")

    # Initialize the ingestor and LLM client
    ingestor = CodeAnalysisIngestor()

    # Create a subclass of OllamaClient to capture the raw response
    class DebugOllamaClient(OllamaClient):
        def generate(self, model, prompt, system=None, options=None):
            response = super().generate(model, prompt, system, options)
            print("\n" + "="*80)
            print("RAW LLM RESPONSE:")
            print("="*80)
            print(response)
            print("="*80 + "\n")
            return response

    # Set the debug client
    ingestor.ollama_client = DebugOllamaClient()

    # Analyze the file
    rel_path = Path(file_path).name
    nodes, edges = ingestor._analyze_javascript_file(file_path, rel_path)

    # Print the results
    print("\nRESULTS:")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")

    if nodes and hasattr(nodes[0], 'imports'):
        print(f"Imports: {nodes[0].imports}")
    else:
        print("No imports found")

    if nodes and hasattr(nodes[0], 'exports'):
        print(f"Exports: {nodes[0].exports}")
    else:
        print("No exports found")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_llm_response.py <js_file_path>")
        sys.exit(1)

    debug_js_analysis(sys.argv[1])
