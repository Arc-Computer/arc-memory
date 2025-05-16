"""
Decision analyzer for the Cross-Repository Explorer.

This module analyzes decisions that span multiple repositories.
"""

import json
from typing import Dict, List, Any


def analyze_decisions(arc, repo_ids: List[str], repo_names: Dict[str, str]) -> None:
    """Analyze decisions that span multiple repositories.

    Args:
        arc: Arc Memory instance
        repo_ids: List of repository IDs
        repo_names: Dictionary mapping repository IDs to names
    """
    if not repo_ids or len(repo_ids) < 2:
        print("Need at least two repositories to analyze cross-repository decisions.")
        return

    # Find decisions that affect multiple repositories
    print("Analyzing cross-repository decisions...")
    
    try:
        # First, find all decision nodes
        decision_nodes = []
        for repo_id in repo_ids:
            repo_name = repo_names.get(repo_id, repo_id)
            
            # Get decision nodes for this repository
            cursor = arc.adapter.conn.execute(
                """
                SELECT id, title, body, extra
                FROM nodes
                WHERE repo_id = ? AND (type = 'decision' OR type = 'pr' OR type = 'issue')
                """,
                (repo_id,)
            )
            nodes = cursor.fetchall()
            
            for node in nodes:
                node["repo_id"] = repo_id
                decision_nodes.append(node)
            
            print(f"Found {len(nodes)} potential decision nodes in {repo_name}.")
    except Exception as e:
        print(f"Error finding decision nodes: {e}")
        return

    # Find decisions that have connections to multiple repositories
    cross_repo_decisions = []
    
    for decision in decision_nodes:
        try:
            # Get all nodes connected to this decision
            cursor = arc.adapter.conn.execute(
                """
                SELECT n.id, n.repo_id, n.type, n.title, e.rel
                FROM edges e
                JOIN nodes n ON e.dst = n.id
                WHERE e.src = ?
                UNION
                SELECT n.id, n.repo_id, n.type, n.title, e.rel
                FROM edges e
                JOIN nodes n ON e.src = n.id
                WHERE e.dst = ?
                """,
                (decision["id"], decision["id"])
            )
            connected_nodes = cursor.fetchall()
            
            # Check if connected nodes span multiple repositories
            connected_repos = set(node["repo_id"] for node in connected_nodes)
            if len(connected_repos) > 1:
                # This decision spans multiple repositories
                decision["connected_nodes"] = connected_nodes
                decision["connected_repos"] = list(connected_repos)
                cross_repo_decisions.append(decision)
        except Exception as e:
            print(f"Error analyzing connections for decision {decision['id']}: {e}")

    # Display cross-repository decisions
    if not cross_repo_decisions:
        print("\nNo cross-repository decisions found.")
        print("This could be because:")
        print("1. There are no decisions that span multiple repositories")
        print("2. The knowledge graph doesn't have sufficient decision information")
        print("3. The repositories have independent decision processes")
        return

    print(f"\nFound {len(cross_repo_decisions)} decisions that span multiple repositories.")
    
    # Sort decisions by the number of repositories they span
    cross_repo_decisions.sort(key=lambda d: len(d["connected_repos"]), reverse=True)
    
    # Display the top decisions
    for i, decision in enumerate(cross_repo_decisions[:5]):
        title = decision["title"]
        body = decision.get("body", "")
        
        # Get affected repositories
        affected_repos = []
        for repo_id in decision["connected_repos"]:
            repo_name = repo_names.get(repo_id, repo_id)
            affected_repos.append(repo_name)
        
        # Get related PRs and issues
        related_items = []
        for node in decision["connected_nodes"]:
            if node["type"] in ["pr", "pull_request", "issue"]:
                related_items.append({
                    "type": node["type"],
                    "title": node["title"],
                    "repo": repo_names.get(node["repo_id"], node["repo_id"])
                })
        
        # Display decision information
        print(f"\nDecision {i+1}: \"{title}\"")
        print(f"Affected repositories: {', '.join(affected_repos)}")
        
        if body:
            print(f"Description: {body[:100]}..." if len(body) > 100 else f"Description: {body}")
        
        if related_items:
            print("Related items:")
            for item in related_items[:5]:
                print(f"  - {item['repo']} {item['type'].upper()}: \"{item['title']}\"")
            
            if len(related_items) > 5:
                print(f"  ... and {len(related_items) - 5} more")
    
    if len(cross_repo_decisions) > 5:
        print(f"\n... and {len(cross_repo_decisions) - 5} more cross-repository decisions.")

    print("\nDecision analysis complete.")
    print("Note: This is a simplified view of cross-repository decisions.")
    print("For more detailed analysis, use the Arc Memory SDK directly.")
