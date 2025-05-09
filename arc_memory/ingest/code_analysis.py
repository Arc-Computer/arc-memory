"""Code analysis plugin for Arc Memory.

This module provides a plugin for analyzing code files and extracting
semantic information about functions, classes, and modules.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from arc_memory.llm.ollama_client import OllamaClient
from arc_memory.logging_conf import get_logger
from arc_memory.process.semantic_analysis import _extract_json_from_llm_response
from arc_memory.schema.models import (
    ClassNode,
    Edge,
    EdgeRel,
    FileNode,
    FunctionNode,
    ModuleNode,
    Node,
    NodeType,
)

logger = get_logger(__name__)


class CodeAnalysisIngestor:
    """Ingestor plugin for deep code analysis."""

    def __init__(self):
        """Initialize the code analysis ingestor."""
        self.ollama_client = None
        self.supported_extensions = {
            ".py": self._analyze_python_file,
            ".js": self._analyze_javascript_file,
            ".ts": self._analyze_typescript_file,
            ".java": self._analyze_java_file,
            ".go": self._analyze_go_file,
            ".rs": self._analyze_rust_file,
        }

    def get_name(self) -> str:
        """Return the name of this plugin."""
        return "code_analysis"

    def get_node_types(self) -> List[str]:
        """Return the node types this plugin can create."""
        return [
            NodeType.FUNCTION,
            NodeType.CLASS,
            NodeType.MODULE,
            NodeType.COMPONENT,
            NodeType.SERVICE,
        ]

    def get_edge_types(self) -> List[str]:
        """Return the edge types this plugin can create."""
        return [
            EdgeRel.CONTAINS,
            EdgeRel.CALLS,
            EdgeRel.IMPORTS,
            EdgeRel.INHERITS_FROM,
            EdgeRel.IMPLEMENTS,
            EdgeRel.PART_OF,
        ]

    def ingest(
        self,
        repo_path: Path,
        last_processed: Optional[Dict[str, Any]] = None,
        llm_enhancement_level: str = "standard",
        ollama_client: Optional[OllamaClient] = None,
    ) -> Tuple[List[Node], List[Edge], Dict[str, Any]]:
        """Ingest code data from a repository.

        Args:
            repo_path: Path to the repository.
            last_processed: Metadata from the previous run for incremental builds.
            llm_enhancement_level: Level of LLM enhancement to apply.
            ollama_client: Optional Ollama client for LLM processing.

        Returns:
            A tuple of (nodes, edges, metadata).
        """
        logger.info(f"Ingesting code analysis data from {repo_path}")

        # Initialize Ollama client if needed
        if llm_enhancement_level != "none":
            self.ollama_client = ollama_client or OllamaClient()

        # Get all code files in the repository
        code_files = self._get_code_files(repo_path)
        logger.info(f"Found {len(code_files)} code files to analyze")

        # Process files
        nodes = []
        edges = []
        processed_files = 0

        for file_path in code_files:
            try:
                # Skip files that are too large
                if os.path.getsize(file_path) > 1_000_000:  # 1MB
                    logger.warning(f"Skipping large file: {file_path}")
                    continue

                # Get file extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in self.supported_extensions:
                    continue

                # Get relative path
                rel_path = os.path.relpath(file_path, repo_path)
                logger.debug(f"Analyzing {rel_path}")

                # Analyze file
                file_nodes, file_edges = self.supported_extensions[ext](file_path, rel_path)
                nodes.extend(file_nodes)
                edges.extend(file_edges)

                processed_files += 1
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")

        # Apply LLM enhancements if enabled
        if llm_enhancement_level != "none" and self.ollama_client:
            nodes, edges = self._enhance_with_llm(nodes, edges, llm_enhancement_level)

        # Create metadata
        metadata = {
            "processed_files": processed_files,
            "function_count": len([n for n in nodes if n.type == NodeType.FUNCTION]),
            "class_count": len([n for n in nodes if n.type == NodeType.CLASS]),
            "module_count": len([n for n in nodes if n.type == NodeType.MODULE]),
            "timestamp": "",  # Will be filled by the build process
        }

        logger.info(
            f"Processed {processed_files} files, extracted {len(nodes)} nodes and {len(edges)} edges"
        )
        return nodes, edges, metadata

    def _get_code_files(self, repo_path: Path) -> List[str]:
        """Get all code files in the repository.

        Args:
            repo_path: Path to the repository.

        Returns:
            A list of file paths.
        """
        code_files = []
        for root, _, files in os.walk(repo_path):
            # Skip hidden directories and common non-code directories
            if any(
                part.startswith(".")
                or part in ["node_modules", "venv", "env", "__pycache__", "build", "dist"]
                for part in Path(root).parts
            ):
                continue

            for file in files:
                # Skip hidden files
                if file.startswith("."):
                    continue

                # Check if file has a supported extension
                ext = os.path.splitext(file)[1].lower()
                if ext in self.supported_extensions:
                    code_files.append(os.path.join(root, file))

        return code_files

    def _analyze_python_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a Python file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        nodes = []
        edges = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse the AST
            tree = ast.parse(content)

            # Create module node
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            module_id = f"module:{rel_path}"
            module_node = ModuleNode(
                id=module_id,
                type=NodeType.MODULE,
                title=module_name,
                path=rel_path,
                name=module_name,
                docstring=ast.get_docstring(tree),
            )
            nodes.append(module_node)

            # Create file-module edge
            file_id = f"file:{rel_path}"
            file_module_edge = Edge(
                src=file_id,
                dst=module_id,
                rel=EdgeRel.CONTAINS,
            )
            edges.append(file_module_edge)

            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Update module node with imports
            module_node.imports = imports

            # Process classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_nodes, class_edges = self._process_python_class(node, rel_path, module_id)
                    nodes.extend(class_nodes)
                    edges.extend(class_edges)
                elif isinstance(node, ast.FunctionDef):
                    func_node, func_edges = self._process_python_function(node, rel_path, module_id)
                    nodes.append(func_node)
                    edges.extend(func_edges)

            return nodes, edges
        except Exception as e:
            logger.error(f"Error analyzing Python file {file_path}: {e}")
            return [], []

    def _process_python_class(
        self, node: ast.ClassDef, file_path: str, module_id: str
    ) -> Tuple[List[Node], List[Edge]]:
        """Process a Python class definition.

        Args:
            node: The AST node for the class.
            file_path: Path to the file.
            module_id: ID of the parent module.

        Returns:
            A tuple of (nodes, edges).
        """
        nodes = []
        edges = []

        # Create class node
        class_id = f"class:{file_path}:{node.name}"
        class_node = ClassNode(
            id=class_id,
            type=NodeType.CLASS,
            title=node.name,
            path=file_path,
            name=node.name,
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
        )
        nodes.append(class_node)

        # Create module-class edge
        module_class_edge = Edge(
            src=module_id,
            dst=class_id,
            rel=EdgeRel.CONTAINS,
        )
        edges.append(module_class_edge)

        # Process inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                # Simple inheritance from a class in the same module
                base_id = f"class:{file_path}:{base.id}"
                inheritance_edge = Edge(
                    src=class_id,
                    dst=base_id,
                    rel=EdgeRel.INHERITS_FROM,
                )
                edges.append(inheritance_edge)

        # Process methods
        method_names = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_node, method_edges = self._process_python_function(
                    item, file_path, class_id, is_method=True
                )
                nodes.append(method_node)
                edges.extend(method_edges)
                method_names.append(item.name)

        # Update class node with methods
        class_node.methods = method_names

        return nodes, edges

    def _process_python_function(
        self, node: ast.FunctionDef, file_path: str, parent_id: str, is_method: bool = False
    ) -> Tuple[Node, List[Edge]]:
        """Process a Python function definition.

        Args:
            node: The AST node for the function.
            file_path: Path to the file.
            parent_id: ID of the parent node (module or class).
            is_method: Whether this is a method of a class.

        Returns:
            A tuple of (node, edges).
        """
        edges = []

        # Get function signature
        params = []
        for arg in node.args.args:
            param_type = ""
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Attribute):
                    param_type = f"{arg.annotation.value.id}.{arg.annotation.attr}"
            params.append({"name": arg.arg, "type": param_type})

        # Get return type
        return_type = ""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                return_type = f"{node.returns.value.id}.{node.returns.attr}"

        # Create function node
        func_id = f"function:{file_path}:{node.name}"
        func_node = FunctionNode(
            id=func_id,
            type=NodeType.FUNCTION,
            title=node.name,
            path=file_path,
            name=node.name,
            signature=f"def {node.name}({', '.join(arg['name'] for arg in params)})",
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
            parameters=params,
            return_type=return_type,
        )

        # Create parent-function edge
        parent_func_edge = Edge(
            src=parent_id,
            dst=func_id,
            rel=EdgeRel.CONTAINS,
        )
        edges.append(parent_func_edge)

        return func_node, edges

    def _analyze_javascript_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a JavaScript file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        # This is a placeholder for JavaScript analysis
        # In a real implementation, we would use a JavaScript parser like esprima
        logger.debug(f"JavaScript analysis not fully implemented for {rel_path}")

        # Create a basic module node
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_id = f"module:{rel_path}"
        module_node = ModuleNode(
            id=module_id,
            type=NodeType.MODULE,
            title=module_name,
            path=rel_path,
            name=module_name,
        )

        # Create file-module edge
        file_id = f"file:{rel_path}"
        file_module_edge = Edge(
            src=file_id,
            dst=module_id,
            rel=EdgeRel.CONTAINS,
        )

        # If LLM enhancement is enabled, use it to extract more information
        if self.ollama_client:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Use LLM to extract functions and classes
                prompt = f"""
                Analyze this JavaScript file and extract information about:
                1. Functions (name, parameters, return type if specified)
                2. Classes (name, methods, properties)
                3. Imports/exports

                Format your response as JSON with the following structure:
                {{
                    "functions": [
                        {{ "name": "functionName", "parameters": ["param1", "param2"], "returnType": "type" }}
                    ],
                    "classes": [
                        {{ "name": "ClassName", "methods": ["method1", "method2"], "properties": ["prop1", "prop2"] }}
                    ],
                    "imports": ["import1", "import2"],
                    "exports": ["export1", "export2"]
                }}

                Here's the JavaScript code:
                ```javascript
                {content[:5000]}  # Limit to first 5000 chars
                ```

                Return ONLY the JSON object, nothing else. Do not include any explanations or markdown formatting.
                """

                system_prompt = """You are a code analysis assistant that extracts structured information from code files.
                Always respond with valid JSON only. Do not include any explanations, markdown formatting, or additional text.
                Ensure all JSON keys and string values are properly quoted with double quotes."""

                response = self.ollama_client.generate(
                    model="qwen3:4b",
                    prompt=prompt,
                    system=system_prompt,
                    options={"temperature": 0.2}
                )

                # Parse the response
                try:
                    # Use the robust JSON extraction function
                    data = _extract_json_from_llm_response(response)

                    # Update module node with imports/exports
                    if "imports" in data:
                        module_node.imports = data["imports"]
                    if "exports" in data:
                        module_node.exports = data["exports"]

                    # Process functions and classes
                    # (Implementation would go here)
                except ValueError as e:
                    logger.warning(f"Could not parse JSON from LLM response for {rel_path}: {e}")

                    # Try a more aggressive fallback approach with manual regex extraction
                    try:
                        # Initialize empty lists for imports and exports
                        imports = []
                        exports = []

                        # Look for imports array
                        imports_match = re.search(r'"imports"\s*:\s*\[(.*?)\]', response, re.DOTALL)
                        if imports_match:
                            imports_str = imports_match.group(1)
                            # Extract quoted strings
                            imports = re.findall(r'"([^"]*)"', imports_str)
                            module_node.imports = imports
                            logger.info(f"Extracted {len(imports)} imports using regex fallback for {rel_path}")

                        # Look for exports array
                        exports_match = re.search(r'"exports"\s*:\s*\[(.*?)\]', response, re.DOTALL)
                        if exports_match:
                            exports_str = exports_match.group(1)
                            # Extract quoted strings
                            exports = re.findall(r'"([^"]*)"', exports_str)
                            module_node.exports = exports
                            logger.info(f"Extracted {len(exports)} exports using regex fallback for {rel_path}")

                        # Update data variable for consistent downstream processing
                        data = {
                            "functions": [],
                            "classes": [],
                            "imports": imports,
                            "exports": exports
                        }
                        logger.info(f"Created data structure from regex fallback for {rel_path}")
                    except Exception as regex_error:
                        logger.warning(f"Regex fallback also failed for {rel_path}: {regex_error}")
                        # Use default empty structure as last resort
                        data = {"functions": [], "classes": [], "imports": [], "exports": []}
                        logger.info(f"Using default empty structure for {rel_path}")
                except Exception as e:
                    logger.error(f"Error processing LLM response for {rel_path}: {e}")
            except Exception as e:
                logger.error(f"Error using LLM for JavaScript analysis of {rel_path}: {e}")

        return [module_node], [file_module_edge]

    def _analyze_typescript_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a TypeScript file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        # TypeScript analysis would be similar to JavaScript but with type information
        # For now, we'll use the same implementation as JavaScript
        return self._analyze_javascript_file(file_path, rel_path)

    def _analyze_java_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a Java file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        # Placeholder for Java analysis
        logger.debug(f"Java analysis not fully implemented for {rel_path}")

        # Create a basic module node
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_id = f"module:{rel_path}"
        module_node = ModuleNode(
            id=module_id,
            type=NodeType.MODULE,
            title=module_name,
            path=rel_path,
            name=module_name,
        )

        # Create file-module edge
        file_id = f"file:{rel_path}"
        file_module_edge = Edge(
            src=file_id,
            dst=module_id,
            rel=EdgeRel.CONTAINS,
        )

        return [module_node], [file_module_edge]

    def _analyze_go_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a Go file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        # Placeholder for Go analysis
        logger.debug(f"Go analysis not fully implemented for {rel_path}")

        # Create a basic module node
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_id = f"module:{rel_path}"
        module_node = ModuleNode(
            id=module_id,
            type=NodeType.MODULE,
            title=module_name,
            path=rel_path,
            name=module_name,
        )

        # Create file-module edge
        file_id = f"file:{rel_path}"
        file_module_edge = Edge(
            src=file_id,
            dst=module_id,
            rel=EdgeRel.CONTAINS,
        )

        return [module_node], [file_module_edge]

    def _analyze_rust_file(self, file_path: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Analyze a Rust file.

        Args:
            file_path: Path to the file.
            rel_path: Relative path from the repository root.

        Returns:
            A tuple of (nodes, edges).
        """
        # Placeholder for Rust analysis
        logger.debug(f"Rust analysis not fully implemented for {rel_path}")

        # Create a basic module node
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_id = f"module:{rel_path}"
        module_node = ModuleNode(
            id=module_id,
            type=NodeType.MODULE,
            title=module_name,
            path=rel_path,
            name=module_name,
        )

        # Create file-module edge
        file_id = f"file:{rel_path}"
        file_module_edge = Edge(
            src=file_id,
            dst=module_id,
            rel=EdgeRel.CONTAINS,
        )

        return [module_node], [file_module_edge]

    def _enhance_with_llm(
        self, nodes: List[Node], edges: List[Edge], enhancement_level: str
    ) -> Tuple[List[Node], List[Edge]]:
        """Enhance nodes and edges with LLM-derived insights.

        Args:
            nodes: List of nodes to enhance.
            edges: List of edges to enhance.
            enhancement_level: Level of enhancement to apply.

        Returns:
            Enhanced nodes and edges.
        """
        if not self.ollama_client:
            return nodes, edges

        logger.info(f"Enhancing code analysis with LLM ({enhancement_level} level)")

        # Group nodes by file for batch processing
        files_to_nodes = {}
        for node in nodes:
            if hasattr(node, "path"):
                if node.path not in files_to_nodes:
                    files_to_nodes[node.path] = []
                files_to_nodes[node.path].append(node)

        # Process each file
        for file_path, file_nodes in files_to_nodes.items():
            # Skip if no nodes to enhance
            if not file_nodes:
                continue

            # Get node IDs for this file
            node_ids = [node.id for node in file_nodes]

            # Get related edges
            file_edges = [
                edge for edge in edges
                if edge.src in node_ids or edge.dst in node_ids
            ]

            # Apply enhancements based on level
            if enhancement_level == "fast":
                # Basic enhancement - just add embeddings
                self._add_embeddings(file_nodes)
            elif enhancement_level == "standard":
                # Standard enhancement - add embeddings and infer relationships
                self._add_embeddings(file_nodes)
                new_edges = self._infer_relationships(file_nodes, file_edges)
                edges.extend(new_edges)
            elif enhancement_level == "deep":
                # Deep enhancement - add embeddings, infer relationships, and add semantic metadata
                self._add_embeddings(file_nodes)
                new_edges = self._infer_relationships(file_nodes, file_edges)
                edges.extend(new_edges)
                self._add_semantic_metadata(file_nodes)

        return nodes, edges

    def _add_embeddings(self, nodes: List[Node]) -> None:
        """Add code embeddings to nodes.

        Args:
            nodes: List of nodes to enhance with embeddings.
        """
        # This is a placeholder for adding embeddings
        # In a real implementation, we would use a code embedding model
        logger.debug(f"Adding embeddings to {len(nodes)} nodes")

        # For now, we'll just add dummy embeddings
        for node in nodes:
            if hasattr(node, "embedding"):
                node.embedding = [0.0] * 10  # Dummy embedding

    def _infer_relationships(self, nodes: List[Node], edges: List[Edge]) -> List[Edge]:
        """Infer relationships between nodes.

        Args:
            nodes: List of nodes to analyze.
            edges: Existing edges between these nodes.

        Returns:
            New inferred edges.
        """
        # This is a placeholder for relationship inference
        logger.debug(f"Inferring relationships for {len(nodes)} nodes")

        # For now, return an empty list
        return []

    def _add_semantic_metadata(self, nodes: List[Node]) -> None:
        """Add semantic metadata to nodes.

        Args:
            nodes: List of nodes to enhance with semantic metadata.
        """
        # This is a placeholder for adding semantic metadata
        logger.debug(f"Adding semantic metadata to {len(nodes)} nodes")

        # For now, we'll just add dummy metadata
        for node in nodes:
            if not node.extra:
                node.extra = {}
            node.extra["semantic_role"] = "unknown"
