#!/usr/bin/env python3
"""
Test script for GitHub PR comment integration.

This script simulates the PR comment generation process that would
happen in a GitHub Actions workflow.

Usage:
    python test_pr_comment.py --repo-path /path/to/repo --pr-sha abc123

Requirements:
    - Arc Memory installed: pip install arc-memory[github,openai]
    - GitHub token: export GITHUB_TOKEN=your-token
    - OpenAI API key (optional): export OPENAI_API_KEY=your-key
"""

import os
import sys
import time
import argparse
import tempfile
from pathlib import Path

from arc_memory import Arc
from arc_memory.auto_refresh import refresh_knowledge_graph


def test_pr_comment(repo_path, pr_sha, use_openai=False):
    """
    Test generating a PR comment.
    
    Args:
        repo_path: Path to the repository
        pr_sha: SHA of the PR head commit
        use_openai: Whether to use OpenAI for enhancement
        
    Returns:
        The generated PR comment
    """
    # Check if GitHub token is set
    if "GITHUB_TOKEN" not in os.environ:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set your GitHub token:")
        print("export GITHUB_TOKEN=your-token")
        sys.exit(1)
    
    # Check if OpenAI API key is set if using OpenAI
    if use_openai and "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY=your-api-key")
        sys.exit(1)
    
    # Create temporary directory for output
    temp_dir = tempfile.mkdtemp()
    export_path = Path(temp_dir) / "pr_analysis.json"
    comment_path = Path(temp_dir) / "pr_analysis.md"
    
    print(f"Testing PR comment generation")
    print(f"Repository path: {repo_path}")
    print(f"PR SHA: {pr_sha}")
    print(f"Using OpenAI: {use_openai}")
    print(f"Temporary directory: {temp_dir}")
    
    # Build knowledge graph
    print("\n=== Building knowledge graph ===")
    start_time = time.time()
    refresh_result = refresh_knowledge_graph(
        repo_path=repo_path,
        include_github=True,
        include_linear=False,
        use_llm=use_openai,
        llm_provider="openai" if use_openai else None,
        llm_model="gpt-3.5-turbo" if use_openai else None,
        verbose=True
    )
    elapsed = time.time() - start_time
    
    print(f"\nKnowledge graph built in {elapsed:.2f} seconds")
    print(f"Added {refresh_result.nodes_added} nodes and {refresh_result.edges_added} edges")
    print(f"Updated {refresh_result.nodes_updated} nodes and {refresh_result.edges_updated} edges")
    
    # Initialize Arc
    arc = Arc(repo_path=repo_path)
    
    # Export the knowledge graph for the PR
    print("\n=== Exporting knowledge graph for PR ===")
    start_time = time.time()
    export_result = arc.export_graph(
        pr_sha=pr_sha,
        output_path=str(export_path),
        compress=True,
        sign=False,
        base_branch="main",
        max_hops=3,
        optimize_for_llm=True,
        include_causal=True
    )
    elapsed = time.time() - start_time
    
    print(f"\nKnowledge graph exported in {elapsed:.2f} seconds")
    print(f"Export path: {export_result.file_path}")
    print(f"Export size: {export_result.file_size} bytes")
    
    # Generate PR analysis
    print("\n=== Generating PR analysis ===")
    start_time = time.time()
    
    # This would normally be done with the CLI command:
    # arc ci analyze --pr $PR_NUMBER --output-format markdown > pr_analysis.md
    # But we'll simulate it here
    
    # Get the files changed in the PR
    changed_files = arc.get_pr_files(pr_sha)
    
    # Get the impact of the changes
    impact_results = []
    for file_path in changed_files:
        component_id = f"file:{file_path}"
        try:
            impact = arc.analyze_component_impact(component_id=component_id, max_depth=2)
            impact_results.extend(impact)
        except Exception as e:
            print(f"Error analyzing impact for {component_id}: {e}")
    
    # Get the decision trail for the PR
    decision_trail = arc.get_decision_trail_for_pr(pr_sha)
    
    # Generate the PR comment
    comment = f"""## Arc Memory Analysis

This automated analysis is powered by [Arc Memory](https://github.com/Arc-Computer/arc-memory).

### 📊 PR Overview

This PR modifies **{len(changed_files)}** files with potential impact on **{len(impact_results)}** components.

### 🔍 Key Insights

"""
    
    # Add impact analysis
    if impact_results:
        comment += "#### Impact Analysis\n\n"
        for i, result in enumerate(impact_results[:5]):  # Limit to top 5
            comment += f"- **{result.title}**: Impact score {result.impact_score:.2f} ({result.impact_type})\n"
        
        if len(impact_results) > 5:
            comment += f"\n<details>\n<summary>Show {len(impact_results) - 5} more affected components</summary>\n\n"
            for result in impact_results[5:]:
                comment += f"- **{result.title}**: Impact score {result.impact_score:.2f} ({result.impact_type})\n"
            comment += "</details>\n"
    else:
        comment += "No significant impact detected for this change.\n"
    
    # Add decision trail
    if decision_trail:
        comment += "\n#### Decision Trail\n\n"
        comment += "<details>\n<summary>Show decision trail</summary>\n\n"
        for entry in decision_trail:
            comment += f"- **{entry.title}**\n"
            comment += f"  - Rationale: {entry.rationale}\n"
            comment += f"  - Importance: {entry.importance}\n\n"
        comment += "</details>\n"
    
    # Add recommendations
    comment += "\n### 💡 Recommendations\n\n"
    comment += "- Consider adding tests for the affected components\n"
    comment += "- Update documentation to reflect these changes\n"
    comment += "- Review the impact on dependent components\n"
    
    # Add feedback section
    comment += """
<details>
<summary>How to improve this analysis</summary>

- Add more context to your PR description
- Link to related issues and PRs
- Build a more comprehensive knowledge graph with `arc build --llm-enhancement`
- Provide feedback by reacting to this comment
</details>
"""
    
    # Write the comment to a file
    with open(comment_path, "w") as f:
        f.write(comment)
    
    elapsed = time.time() - start_time
    print(f"\nPR analysis generated in {elapsed:.2f} seconds")
    print(f"Comment path: {comment_path}")
    
    # Print the comment
    print("\n=== PR Comment ===\n")
    print(comment)
    
    return {
        "export_path": str(export_path),
        "comment_path": str(comment_path),
        "comment": comment,
        "changed_files": changed_files,
        "impact_results": impact_results,
        "decision_trail": decision_trail
    }


def main():
    parser = argparse.ArgumentParser(description="Test PR comment generation for Arc Memory")
    parser.add_argument("--repo-path", default="./", help="Path to the repository")
    parser.add_argument("--pr-sha", required=True, help="SHA of the PR head commit")
    parser.add_argument("--use-openai", action="store_true", help="Use OpenAI for enhancement")
    args = parser.parse_args()
    
    test_pr_comment(args.repo_path, args.pr_sha, args.use_openai)


if __name__ == "__main__":
    main()
