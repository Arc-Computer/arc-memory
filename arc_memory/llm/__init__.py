"""LLM integration for Arc Memory.

This module provides integration with language models for enhancing
the knowledge graph with semantic understanding and reasoning.
"""

from arc_memory.llm.ollama_client import OllamaClient, ensure_ollama_available

__all__ = ["OllamaClient", "ensure_ollama_available"]
