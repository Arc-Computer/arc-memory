#!/usr/bin/env python3
"""
Simplified Self-Healing Code Generation Loop

This script demonstrates a simplified approach to self-healing code generation
using OpenAI's capabilities. It coordinates three specialized agents to improve code quality:

1. Code Review Agent: Analyzes code quality and identifies issues
2. Impact Analysis Agent: Determines potential impacts of changes
3. Code Generation Agent: Creates improved code based on insights

Usage: python simplified_self_healing_loop.py --file /path/to/file.py [--output improved_file.py]
"""

import os
import sys
import argparse
import json
import logging
import colorama
from colorama import Fore, Style
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress verbose logs from dependencies
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def get_file_content(file_path: str) -> str:
    """Get the content of a file."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Could not read file {file_path}: {e}")
        return ""

def run_code_review(file_path: str) -> Dict[str, Any]:
    """Run code review on a file using Arc Memory and OpenAI."""
    logger.info(f"Running code review on {file_path}")

    # Get file content
    file_content = get_file_content(file_path)
    if not file_content:
        return {"error": f"Could not read file {file_path}"}

    # Create a prompt for code review
    prompt = f"""
    Please review the following code and identify issues, patterns, and potential improvements:

    ```python
    {file_content}
    ```

    Focus on:
    1. Code quality issues
    2. Potential bugs
    3. Performance concerns
    4. Best practices violations

    Provide a detailed analysis with specific recommendations for improvement.
    """

    try:
        # Use OpenAI directly instead of the adapter
        import openai

        # Create a client
        client = openai.OpenAI()

        # Call the API
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": """You are a code review expert. Analyze code thoroughly and provide
                specific, actionable feedback to improve code quality, performance, and maintainability."""},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the content
        review = response.choices[0].message.content

        return {
            "success": True,
            "review": review,
        }
    except Exception as e:
        logger.error(f"Error in code review: {e}")
        return {"error": str(e)}

def run_impact_analysis(file_path: str) -> Dict[str, Any]:
    """Analyze potential impacts of changes to a file."""
    logger.info(f"Running impact analysis on {file_path}")

    # Get file content
    file_content = get_file_content(file_path)
    if not file_content:
        return {"error": f"Could not read file {file_path}"}

    # Create a prompt for impact analysis
    prompt = f"""
    Please analyze the potential impacts of changes to the following file:

    ```python
    {file_content}
    ```

    Focus on:
    1. Which components might be affected by changes to this file
    2. Potential risks associated with modifying this file
    3. Recommendations for safely making changes

    Provide a detailed analysis of the potential blast radius of changes.
    """

    try:
        # Use OpenAI directly instead of the adapter
        import openai

        # Create a client
        client = openai.OpenAI()

        # Call the API
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": """You are an impact analysis expert. Analyze the potential impacts
                of code changes and provide specific recommendations for minimizing risks."""},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the content
        impact_analysis = response.choices[0].message.content

        return {
            "success": True,
            "impact_analysis": impact_analysis,
        }
    except Exception as e:
        logger.error(f"Error in impact analysis: {e}")
        return {"error": str(e)}

def generate_improved_code(file_path: str, review: str, impact_analysis: str) -> Dict[str, Any]:
    """Generate improved code based on review and impact analysis."""
    logger.info(f"Generating improved code for {file_path}")

    # Get file content
    file_content = get_file_content(file_path)
    if not file_content:
        return {"error": f"Could not read file {file_path}"}

    # Create a prompt for code generation
    prompt = f"""
    I need you to improve the following code based on the code review and impact analysis provided.

    Original code:
    ```python
    {file_content}
    ```

    Code Review:
    {review}

    Impact Analysis:
    {impact_analysis}

    Please generate an improved version of this code that:
    1. Addresses the issues identified in the code review
    2. Minimizes negative impacts identified in the impact analysis
    3. Follows best practices and patterns
    4. Maintains compatibility with dependent components

    Return your response in the following JSON format:
    {{
        "code": "// Your improved code here with proper indentation and formatting",
        "explanations": [
            "Explanation 1",
            "Explanation 2",
            "..."
        ]
    }}
    """

    try:
        # Use OpenAI directly instead of the adapter
        import openai

        # Create a client
        client = openai.OpenAI()

        # Call the API
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": """You are a code improvement expert. Generate improved code based on
                review feedback and impact analysis. Always return your response in valid JSON format
                with 'code' and 'explanations' fields."""},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the content
        result_content = response.choices[0].message.content

        # Parse the JSON response
        try:
            response_data = json.loads(result_content)
            return {
                "success": True,
                "improved_code": response_data.get("code", ""),
                "explanations": response_data.get("explanations", [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"error": f"Failed to parse JSON response: {e}"}

    except Exception as e:
        logger.error(f"Error generating improved code: {e}")
        return {"error": str(e)}

def run_self_healing_loop(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the simplified self-healing loop on a file."""
    print(f"{Fore.GREEN}=== Starting Simplified Self-Healing Loop ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}File: {file_path}{Style.RESET_ALL}")

    # Step 1: Run code review
    print(f"\n{Fore.CYAN}Step 1: Running Code Review{Style.RESET_ALL}")
    review_results = run_code_review(file_path)
    if "error" in review_results:
        print(f"{Fore.RED}Code Review failed: {review_results['error']}{Style.RESET_ALL}")
        return {"error": review_results["error"]}

    print(f"{Fore.GREEN}Code Review completed successfully{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Review Highlights:{Style.RESET_ALL}")
    review_highlights = review_results["review"].split("\n\n")[0]
    print(f"{review_highlights}\n")

    # Step 2: Run impact analysis
    print(f"\n{Fore.CYAN}Step 2: Running Impact Analysis{Style.RESET_ALL}")
    impact_results = run_impact_analysis(file_path)
    if "error" in impact_results:
        print(f"{Fore.RED}Impact Analysis failed: {impact_results['error']}{Style.RESET_ALL}")
        return {"error": impact_results["error"]}

    print(f"{Fore.GREEN}Impact Analysis completed successfully{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Impact Analysis Highlights:{Style.RESET_ALL}")
    impact_highlights = impact_results["impact_analysis"].split("\n\n")[0]
    print(f"{impact_highlights}\n")

    # Step 3: Generate improved code
    print(f"\n{Fore.CYAN}Step 3: Generating Improved Code{Style.RESET_ALL}")
    generation_results = generate_improved_code(
        file_path,
        review_results["review"],
        impact_results["impact_analysis"]
    )

    if "error" in generation_results:
        print(f"{Fore.RED}Code Generation failed: {generation_results['error']}{Style.RESET_ALL}")
        return {"error": generation_results["error"]}

    print(f"{Fore.GREEN}Code Generation completed successfully{Style.RESET_ALL}")

    # Display explanations
    print(f"\n{Fore.CYAN}Improvements Made:{Style.RESET_ALL}")
    for i, explanation in enumerate(generation_results["explanations"], 1):
        print(f"{i}. {explanation}")

    # Save the improved code if requested
    if output_path and generation_results["improved_code"]:
        try:
            with open(output_path, 'w') as f:
                f.write(generation_results["improved_code"])
            print(f"\n{Fore.GREEN}Improved code saved to {output_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}Error saving improved code: {e}{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}=== Self-Healing Loop Complete ==={Style.RESET_ALL}")

    return {
        "success": True,
        "review": review_results["review"],
        "impact_analysis": impact_results["impact_analysis"],
        "improved_code": generation_results["improved_code"],
        "explanations": generation_results["explanations"]
    }

def main():
    """Main entry point for the Simplified Self-Healing Loop."""
    parser = argparse.ArgumentParser(description="Simplified Self-Healing Code Generation Loop")
    parser.add_argument("--file", required=True, help="File to improve")
    parser.add_argument("--output", help="Output file for improved code (optional)")

    args = parser.parse_args()

    # Run the self-healing loop
    results = run_self_healing_loop(args.file, args.output)

    if "error" in results:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
