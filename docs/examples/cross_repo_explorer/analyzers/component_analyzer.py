"""
Component analyzer for the Cross-Repository Explorer.

This module identifies shared components across repositories.
"""

import json
from typing import Dict, List, Any


def analyze_components(arc, repo_ids: List[str], repo_names: Dict[str, str]) -> None:
    """Identify shared components across repositories.

    Args:
        arc: Arc Memory instance
        repo_ids: List of repository IDs
        repo_names: Dictionary mapping repository IDs to names
    """
    if not repo_ids or len(repo_ids) < 2:
        print("Need at least two repositories to analyze shared components.")
        return

    # Find components that exist across multiple repositories
    print("Analyzing shared components across repositories...")
    
    # First, get all components from all repositories
    all_components = {}
    for repo_id in repo_ids:
        repo_name = repo_names.get(repo_id, repo_id)
        
        try:
            # Get component nodes for this repository
            cursor = arc.adapter.conn.execute(
                """
                SELECT id, title, type, extra
                FROM nodes
                WHERE repo_id = ? AND (
                    type = 'component' OR
                    type = 'service' OR
                    type = 'module' OR
                    type = 'interface'
                )
                """,
                (repo_id,)
            )
            components = cursor.fetchall()
            
            # Store components by repository
            all_components[repo_id] = components
            
            print(f"Found {len(components)} components in {repo_name}.")
        except Exception as e:
            print(f"Error getting components for {repo_name}: {e}")

    # Group components by name/functionality across repositories
    component_groups = {}
    
    # First pass: group by exact title match
    for repo_id, components in all_components.items():
        for component in components:
            title = component["title"].lower()
            
            if title not in component_groups:
                component_groups[title] = []
            
            component_groups[title].append({
                "repo_id": repo_id,
                "id": component["id"],
                "title": component["title"],
                "type": component["type"],
                "extra": component["extra"]
            })

    # Second pass: find similar components using related entities
    for repo_id, components in all_components.items():
        for component in components:
            try:
                # Get related entities for this component
                related = arc.get_related_entities(
                    entity_id=component["id"],
                    max_results=20
                )
                
                # Extract keywords from related entities
                keywords = set()
                for entity in related:
                    if hasattr(entity, "title"):
                        words = entity.title.lower().split()
                        keywords.update(words)
                
                # Find similar components in other repositories
                for other_repo_id, other_components in all_components.items():
                    if other_repo_id == repo_id:
                        continue
                    
                    for other_component in other_components:
                        other_title = other_component["title"].lower()
                        
                        # Check for keyword matches
                        match_score = 0
                        for keyword in keywords:
                            if len(keyword) > 3 and keyword in other_title:
                                match_score += 1
                        
                        # If good match, add to a new group
                        if match_score >= 2:
                            group_key = f"{component['title']}|{other_component['title']}"
                            
                            if group_key not in component_groups:
                                component_groups[group_key] = []
                                
                                # Add both components to the group
                                component_groups[group_key].append({
                                    "repo_id": repo_id,
                                    "id": component["id"],
                                    "title": component["title"],
                                    "type": component["type"],
                                    "extra": component["extra"]
                                })
                                
                                component_groups[group_key].append({
                                    "repo_id": other_repo_id,
                                    "id": other_component["id"],
                                    "title": other_component["title"],
                                    "type": other_component["type"],
                                    "extra": other_component["extra"]
                                })
            except Exception as e:
                print(f"Error analyzing related entities for {component['id']}: {e}")

    # Filter for groups that span multiple repositories
    shared_components = {}
    for key, group in component_groups.items():
        # Get unique repositories in this group
        repos = set(component["repo_id"] for component in group)
        
        if len(repos) > 1:
            shared_components[key] = {
                "components": group,
                "repos": list(repos)
            }

    # Display shared components
    if not shared_components:
        print("\nNo shared components found across repositories.")
        print("This could be because:")
        print("1. The repositories truly have no shared components")
        print("2. The knowledge graph doesn't have component information")
        print("3. Components have different names across repositories")
        return

    print(f"\nFound {len(shared_components)} shared components across repositories.")
    
    # Sort shared components by the number of repositories they span
    sorted_components = sorted(
        shared_components.items(),
        key=lambda x: len(x[1]["repos"]),
        reverse=True
    )
    
    # Display the top shared components
    for i, (key, data) in enumerate(sorted_components[:5]):
        components = data["components"]
        repos = data["repos"]
        
        # Get a representative title
        if "|" in key:
            # This is a similar component group
            titles = key.split("|")
            display_title = f"{titles[0]} / {titles[1]}"
        else:
            # This is an exact match group
            display_title = key
        
        # Display component information
        print(f"\nShared Component {i+1}: \"{display_title}\"")
        print(f"Found in {len(repos)} repositories:")
        
        # Group components by repository
        by_repo = {}
        for component in components:
            repo_id = component["repo_id"]
            if repo_id not in by_repo:
                by_repo[repo_id] = []
            by_repo[repo_id].append(component)
        
        # Display components by repository
        for repo_id, repo_components in by_repo.items():
            repo_name = repo_names.get(repo_id, repo_id)
            print(f"  - {repo_name}:")
            
            for component in repo_components:
                print(f"    * {component['type']}: {component['title']}")
                
                # Try to extract file paths from extra data
                try:
                    if component["extra"]:
                        extra = json.loads(component["extra"]) if isinstance(component["extra"], str) else component["extra"]
                        if isinstance(extra, dict) and "path" in extra:
                            print(f"      Path: {extra['path']}")
                except Exception:
                    pass
    
    if len(sorted_components) > 5:
        print(f"\n... and {len(sorted_components) - 5} more shared components.")

    print("\nComponent analysis complete.")
    print("Note: This is a simplified view of shared components across repositories.")
    print("For more detailed analysis, use the Arc Memory SDK directly.")
