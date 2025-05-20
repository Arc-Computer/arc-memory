"""
Data provider for the reinforcement learning pipeline.

This module implements data providers to fetch repository data from GitHub
for training the RL agent on real-world projects.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
import json
import hashlib

import requests
import numpy as np

logger = logging.getLogger(__name__)

class GitHubDataProvider:
    """
    Fetches and processes repository data from GitHub for RL training.
    
    This class provides methods to download commit history, file changes,
    and other data needed to build a temporal graph for RL training.
    """
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str, cache_dir: str = ".github_cache"):
        """
        Initialize the GitHub data provider.
        
        Args:
            github_token: GitHub API token for authentication
            repo_owner: Owner of the repository (user or organization)
            repo_name: Name of the repository
            cache_dir: Directory to store cached API responses
        """
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _generate_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique cache key for an API request."""
        key_string = endpoint
        if params:
            # Sort params by key to ensure consistent key generation
            sorted_params = sorted(params.items())
            key_string += str(sorted_params)
        
        # Use hashlib for a robust and filesystem-friendly hash
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the GitHub API, using a local cache if available.
        
        Args:
            endpoint: API endpoint to request
            params: Query parameters
            
        Returns:
            JSON response
        """
        cache_key = self._generate_cache_key(endpoint, params)
        cache_file_path = os.path.join(self.cache_dir, f"{cache_key}.json")

        # Check cache first
        if os.path.exists(cache_file_path):
            try:
                with open(cache_file_path, 'r') as f:
                    logger.debug(f"Cache hit for {endpoint} with params {params}. Loading from {cache_file_path}")
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error decoding cache file {cache_file_path}. Refetching.")
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file_path}: {e}. Refetching.")

        logger.debug(f"Cache miss for {endpoint} with params {params}. Fetching from API.")
        url = f"{self.base_url}/{endpoint}"
        
        max_attempts = 3  # Max attempts for transient errors
        max_rate_limit_retries = 5  # Max retries for rate limiting to prevent infinite loops
        
        attempt = 0
        rate_limit_retries = 0
        
        while True:  # Main loop that handles both transient errors and rate limiting
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
                    remaining = int(response.headers["X-RateLimit-Remaining"])
                    if remaining == 0:
                        # Check if we've exceeded max rate limit retries
                        if rate_limit_retries >= max_rate_limit_retries:
                            logger.error(f"Exceeded maximum rate limit retries ({max_rate_limit_retries}). Aborting.")
                            raise Exception("GitHub API rate limit exceeded maximum retry attempts")
                            
                        reset_time_str = response.headers.get("X-RateLimit-Reset", str(int(time.time() + 3600)))  # Default to 1hr
                        reset_time = int(reset_time_str)
                        current_time = int(time.time())
                        sleep_time = max(0, reset_time - current_time) + 1  # Add 1 sec buffer
                        
                        logger.info(f"Rate limit exceeded. Remaining: {remaining}. Reset in {reset_time - current_time}s. Sleeping for {sleep_time} seconds. Retry {rate_limit_retries + 1}/{max_rate_limit_retries}")
                        if sleep_time > 3600 * 2:  # Safety: don't sleep for more than 2 hours
                            logger.warning(f"Calculated sleep time {sleep_time}s is too long. Capping at 1 hour.")
                            sleep_time = 3600 
                        
                        time.sleep(sleep_time)
                        rate_limit_retries += 1
                        # Continue the loop to retry the request after sleeping
                        continue
                
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()

                # Save to cache
                try:
                    with open(cache_file_path, 'w') as f:
                        json.dump(data, f)
                    logger.debug(f"Cached response for {endpoint} with params {params} to {cache_file_path}")
                except Exception as e:
                    logger.error(f"Failed to write to cache file {cache_file_path}: {e}")
                
                return data

            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out for {url} with params {params}. Attempt {attempt + 1}/{max_attempts}.")
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Request failed after {max_attempts} timeouts for {url}.")
                    raise
                time.sleep(5 * attempt)  # Exponential backoff for timeouts
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url} with params {params}: {e}. Attempt {attempt + 1}/{max_attempts}.")
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Request failed after {max_attempts} attempts for {url}.")
                    raise  # Reraise the last exception if all attempts fail
                time.sleep(5 * attempt)  # Exponential backoff for other request errors
        
        # This line should not be reached due to the infinite loop with explicit exit conditions
        # If we get here somehow, raise an exception
        raise Exception(f"Failed to fetch data for {url} - unexpected loop exit")
    
    def get_commits(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get commits between the specified dates.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of commits
        """
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/commits"
        params = {
            "since": f"{start_date}T00:00:00Z",
            "until": f"{end_date}T23:59:59Z",
            "per_page": 100
        }
        
        all_commits = []
        page = 1
        
        while True:
            params["page"] = page
            commits = self._make_request(endpoint, params)
            
            if not commits:
                break
                
            all_commits.extend(commits)
            page += 1
            
        return all_commits
    
    def get_commit_details(self, commit_sha: str) -> Dict[str, Any]:
        """
        Get details for a specific commit.
        
        Args:
            commit_sha: Commit SHA
            
        Returns:
            Commit details
        """
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}"
        return self._make_request(endpoint)
    
    def get_file_contents(self, file_path: str, ref: str) -> Dict[str, Any]:
        """
        Get contents of a file at a specific reference.
        
        Args:
            file_path: Path to the file
            ref: Reference (commit SHA, branch, or tag)
            
        Returns:
            File contents
        """
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
        params = {"ref": ref}
        return self._make_request(endpoint, params)
    
    def build_temporal_graph(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Build a temporal graph of the repository.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Temporal graph data
        """
        logger.info(f"Building temporal graph for {self.repo_owner}/{self.repo_name} "
                   f"from {start_date} to {end_date}")
        
        # Get all commits in date range
        commits = self.get_commits(start_date, end_date)
        logger.info(f"Found {len(commits)} commits between {start_date} and {end_date}")
        
        # Build the graph
        graph = {
            "nodes": [],
            "edges": [],
            "commits": []
        }
        
        # Process each commit
        for commit in commits:
            commit_sha = commit["sha"]
            commit_details = self.get_commit_details(commit_sha)
            
            # Add commit to graph
            graph["commits"].append({
                "sha": commit_sha,
                "author": commit_details["commit"]["author"]["name"],
                "date": commit_details["commit"]["author"]["date"],
                "message": commit_details["commit"]["message"]
            })
            
            # Process file changes
            if "files" in commit_details:
                for file_change in commit_details["files"]:
                    filename = file_change["filename"]
                    
                    # Add file node if it doesn't exist
                    if not any(node["id"] == filename for node in graph["nodes"]):
                        graph["nodes"].append({
                            "id": filename,
                            "type": "file",
                            "path": filename
                        })
                    
                    # Add commit-file edge
                    graph["edges"].append({
                        "source": commit_sha,
                        "target": filename,
                        "type": "modifies",
                        "date": commit_details["commit"]["author"]["date"]
                    })
                    
                    # If possible, group files by component/module
                    components = self._infer_component_from_path(filename)
                    for component in components:
                        # Add component node if it doesn't exist
                        if not any(node["id"] == component for node in graph["nodes"]):
                            graph["nodes"].append({
                                "id": component,
                                "type": "component",
                                "name": component
                            })
                        
                        # Add file-component edge
                        graph["edges"].append({
                            "source": filename,
                            "target": component,
                            "type": "belongs_to"
                        })
        
        return graph
    
    def _infer_component_from_path(self, file_path: str) -> List[str]:
        """
        Infer component/module from file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of inferred components
        """
        # Simple heuristic: use first-level directory as component
        parts = file_path.split("/")
        
        components = []
        if len(parts) > 1:
            components.append(parts[0])
            
            # For deeper nested files, also include secondary components
            if len(parts) > 2:
                components.append(f"{parts[0]}/{parts[1]}")
                
        return components
    
    def infer_blast_radius(self, file_path: str, time_window_days: int = 30) -> List[str]:
        """
        Infer blast radius for a given file based on historical co-changes.
        
        Args:
            file_path: Path to the file
            time_window_days: Time window for considering co-changes
            
        Returns:
            List of files in the blast radius
        """
        # Get all commits that modified this file
        endpoint = f"repos/{self.repo_owner}/{self.repo_name}/commits"
        params = {"path": file_path, "per_page": 100}
        
        all_commits = []
        page = 1
        
        while True:
            params["page"] = page
            commits = self._make_request(endpoint, params)
            
            if not commits:
                break
                
            all_commits.extend(commits)
            page += 1
            
        # Get detailed commit info
        blast_radius = set()
        
        for commit in all_commits:
            commit_sha = commit["sha"]
            commit_details = self.get_commit_details(commit_sha)
            
            # Add co-changed files to blast radius
            if "files" in commit_details:
                for file_change in commit_details["files"]:
                    changed_file = file_change["filename"]
                    if changed_file != file_path:
                        blast_radius.add(changed_file)
        
        return list(blast_radius) 