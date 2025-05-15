"""
Reasoning Engine for Code Time Machine Demo

This module provides a reasoning engine that leverages OpenAI's Responses API
with reasoning models to provide intelligent analysis of code evolution,
decision trails, and impact prediction.
"""

import os
import json
from typing import Dict, List, Optional, Any, Union

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    console = Console()
except ImportError:
    print("Required packages not installed. Install with: pip install openai rich")
    import sys
    sys.exit(1)


class ReasoningEngine:
    """Reasoning engine that leverages OpenAI's Responses API with reasoning models."""

    def __init__(self, model: str = "o4-mini"):
        """Initialize the reasoning engine.

        Args:
            model: The OpenAI model to use (default: o4-mini)
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.previous_response_id = None
        self.reasoning_items = []

    def analyze_file_history(self, file_path: str, history: List[Any]) -> Dict[str, Any]:
        """Analyze the history of a file using the reasoning model.

        Args:
            file_path: Path to the file
            history: List of history entries

        Returns:
            Analysis results
        """
        # Format the history entries for the model
        history_text = self._format_history_for_model(history)

        # Create the prompt
        prompt = f"""
        Analyze the history of the file {file_path} based on the following timeline:

        {history_text}

        Provide insights on:
        1. Key development phases and milestones
        2. Patterns in how the file has evolved
        3. Major decisions that shaped the file
        4. Potential reasons for changes based on commit messages and timestamps
        """

        # Call the reasoning model
        response = self._call_reasoning_model(prompt)

        # Extract the analysis from the response
        analysis = {
            "text": response.get("output_text", ""),
            "reasoning_summary": self._extract_reasoning_summary(response)
        }

        return analysis

    def analyze_decisions(self, file_path: str, decision_trails: List[Any]) -> Dict[str, Any]:
        """Analyze the decision trails for a file using the reasoning model.

        Args:
            file_path: Path to the file
            decision_trails: List of decision trail entries

        Returns:
            Analysis results
        """
        # Format the decision trails for the model
        decisions_text = self._format_decisions_for_model(decision_trails)

        # Create the prompt
        prompt = f"""
        Analyze the key decisions that shaped the file {file_path} based on the following decision trails:

        {decisions_text}

        Provide insights on:
        1. The rationale behind each key decision
        2. How these decisions relate to each other
        3. The potential impact of these decisions on the codebase
        4. Alternative approaches that could have been taken
        """

        # Call the reasoning model
        response = self._call_reasoning_model(prompt)

        # Extract the analysis from the response
        analysis = {
            "text": response.get("output_text", ""),
            "reasoning_summary": self._extract_reasoning_summary(response)
        }

        return analysis

    def analyze_impact(self, file_path: str, impact_results: List[Any]) -> Dict[str, Any]:
        """Analyze the potential impact of changes to a file using the reasoning model.

        Args:
            file_path: Path to the file
            impact_results: List of impact results

        Returns:
            Analysis results
        """
        # Format the impact results for the model
        impact_text = self._format_impact_for_model(impact_results)

        # Create the prompt
        prompt = f"""
        Analyze the potential impact of changes to the file {file_path} based on the following impact analysis:

        {impact_text}

        Provide insights on:
        1. The most critical components that would be affected
        2. Potential risks and mitigation strategies
        3. Recommended testing approaches for changes to this file
        4. Suggestions for minimizing the impact of changes
        """

        # Call the reasoning model
        response = self._call_reasoning_model(prompt)

        # Extract the analysis from the response
        analysis = {
            "text": response.get("output_text", ""),
            "reasoning_summary": self._extract_reasoning_summary(response)
        }

        return analysis

    def suggest_improvements(self, file_path: str, file_content: str, history: List[Any], impact_results: List[Any]) -> Dict[str, Any]:
        """Suggest improvements for a file using the reasoning model.

        Args:
            file_path: Path to the file
            file_content: Content of the file
            history: List of history entries
            impact_results: List of impact results

        Returns:
            Improvement suggestions
        """
        # Format the history and impact for the model
        history_text = self._format_history_for_model(history)
        impact_text = self._format_impact_for_model(impact_results)

        # Create the prompt
        prompt = f"""
        Based on the history and impact analysis of the file {file_path}, suggest improvements:

        File History:
        {history_text}

        Impact Analysis:
        {impact_text}

        Provide suggestions for:
        1. Code quality improvements
        2. Performance optimizations
        3. Security enhancements
        4. Documentation improvements
        5. Architectural changes

        For each suggestion, explain the rationale and potential benefits.
        """

        # Call the reasoning model
        response = self._call_reasoning_model(prompt)

        # Extract the suggestions from the response
        suggestions = {
            "text": response.get("output_text", ""),
            "reasoning_summary": self._extract_reasoning_summary(response)
        }

        return suggestions

    def _format_history_for_model(self, history: List[Any]) -> str:
        """Format history entries for the model.

        Args:
            history: List of history entries

        Returns:
            Formatted history text
        """
        if not history:
            return "No history available."

        # Sort history by timestamp (newest first)
        from datetime import datetime

        def sort_key(entry):
            if not hasattr(entry, 'timestamp') or not entry.timestamp:
                return datetime.min  # Default value for sorting

            # Handle different timestamp formats
            if isinstance(entry.timestamp, datetime):
                return entry.timestamp
            elif isinstance(entry.timestamp, str):
                try:
                    # Try to parse ISO format
                    if 'Z' in entry.timestamp:
                        return datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                    else:
                        return datetime.fromisoformat(entry.timestamp)
                except ValueError:
                    # If parsing fails, return min datetime
                    return datetime.min
            else:
                return datetime.min

        sorted_history = sorted(
            history,
            key=sort_key,
            reverse=True
        )

        # Format the history entries
        history_text = ""
        for entry in sorted_history:
            # Get the timestamp
            timestamp = entry.timestamp if hasattr(entry, 'timestamp') else "Unknown date"

            # Get the title
            title = entry.title if hasattr(entry, 'title') and entry.title else "Unknown"

            # Get the type
            entry_type = entry.type if hasattr(entry, 'type') else "unknown"

            # Get the change type
            change_type = entry.change_type if hasattr(entry, 'change_type') else "unknown"

            # Get the author
            author = ""
            if hasattr(entry, 'properties') and entry.properties:
                if 'author' in entry.properties:
                    author = f" by {entry.properties['author']}"

            # Add the entry to the history text
            history_text += f"- {timestamp}: {entry_type.upper()} - {title}{author} ({change_type})\n"

        return history_text

    def _format_decisions_for_model(self, decision_trails: List[Any]) -> str:
        """Format decision trails for the model.

        Args:
            decision_trails: List of decision trail entries

        Returns:
            Formatted decisions text
        """
        if not decision_trails:
            return "No decision trails available."

        # Format the decision trails
        decisions_text = ""
        for line_number, trail in decision_trails:
            if not trail:
                continue

            decisions_text += f"## Line {line_number}\n\n"

            for i, entry in enumerate(trail):
                # Add entry header
                decisions_text += f"### {i+1}. {entry.title}\n\n"

                # Add entry type and ID
                decisions_text += f"**Type:** {entry.type}\n\n"

                # Add rationale if available
                if hasattr(entry, 'rationale') and entry.rationale:
                    decisions_text += f"**Rationale:** {entry.rationale}\n\n"

                # Add properties based on type
                if entry.type == "commit":
                    if hasattr(entry, 'properties'):
                        if 'author' in entry.properties:
                            decisions_text += f"**Author:** {entry.properties['author']}\n\n"
                        if 'sha' in entry.properties:
                            decisions_text += f"**Commit:** {entry.properties['sha'][:7]}\n\n"

                elif entry.type == "pr":
                    if hasattr(entry, 'properties'):
                        if 'number' in entry.properties:
                            decisions_text += f"**PR:** #{entry.properties['number']}\n\n"
                        if 'state' in entry.properties:
                            decisions_text += f"**State:** {entry.properties['state']}\n\n"

                # Add separator between entries
                if i < len(trail) - 1:
                    decisions_text += "---\n\n"

            decisions_text += "\n\n"

        return decisions_text

    def _format_impact_for_model(self, impact_results: List[Any]) -> str:
        """Format impact results for the model.

        Args:
            impact_results: List of impact results

        Returns:
            Formatted impact text
        """
        if not impact_results:
            return "No impact analysis available."

        # Format the impact results
        impact_text = ""
        for result in impact_results:
            # Get the component title
            title = result.title if hasattr(result, 'title') and result.title else "Unknown"

            # Get the impact type
            impact_type = result.impact_type if hasattr(result, 'impact_type') and result.impact_type else "Unknown"

            # Get the impact score
            impact_score = result.impact_score if hasattr(result, 'impact_score') else 0.0

            # Get the impact path
            impact_path = " -> ".join(result.impact_path) if hasattr(result, 'impact_path') and result.impact_path else ""

            # Add the result to the impact text
            impact_text += f"- {title} (Type: {impact_type}, Score: {impact_score:.2f})\n"
            if impact_path:
                impact_text += f"  Path: {impact_path}\n"

        return impact_text

    def _call_reasoning_model(self, prompt: str) -> Dict[str, Any]:
        """Call the reasoning model with a prompt.

        Args:
            prompt: The prompt to send to the model

        Returns:
            The model's response
        """
        try:
            # Create the input context
            context = [{"role": "user", "content": prompt}]

            # Add previous reasoning items if available
            if self.reasoning_items:
                context.extend(self.reasoning_items)

            # Call the model
            response = self.client.responses.create(
                model=self.model,
                input=context,
                reasoning={"summary": "auto"},
                previous_response_id=self.previous_response_id
            )

            # Store the response ID for future calls
            self.previous_response_id = response.id

            # Extract the output text
            output_text = response.output_text if hasattr(response, 'output_text') else ""

            # Return the response
            return {
                "output_text": output_text,
                "response": response
            }

        except Exception as e:
            console.print(f"[red]Error calling reasoning model: {e}[/red]")
            return {"output_text": f"Error: {e}", "response": None}

    def _extract_reasoning_summary(self, response: Dict[str, Any]) -> str:
        """Extract the reasoning summary from a response.

        Args:
            response: The model's response

        Returns:
            The reasoning summary
        """
        if not response or "response" not in response or not response["response"]:
            return ""

        # Get the response object
        response_obj = response["response"]

        # Extract the reasoning summary
        reasoning_summary = ""
        if hasattr(response_obj, 'output') and response_obj.output:
            for item in response_obj.output:
                if hasattr(item, 'type') and item.type == 'reasoning':
                    if hasattr(item, 'summary') and item.summary:
                        for summary in item.summary:
                            if hasattr(summary, 'text'):
                                reasoning_summary += summary.text + "\n\n"

        return reasoning_summary
