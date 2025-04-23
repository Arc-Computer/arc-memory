#!/usr/bin/env python3
"""Test script for GitHub App authentication."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from arc_memory.auth.github import (
    GitHubAppConfig,
    get_installation_token_for_repo,
    store_github_app_config_in_keyring,
)

def main():
    """Test GitHub App authentication."""
    # Read private key from file
    private_key_path = "/Users/jarrodbarnes/Downloads/Arc_Memory_Private_Key_Apr_23_2025.pem"
    try:
        with open(private_key_path, "r") as f:
            private_key = f.read()
    except Exception as e:
        print(f"Failed to read private key file: {e}")
        sys.exit(1)

    # Create GitHub App config
    config = GitHubAppConfig(
        app_id="1227868",
        private_key=private_key,
        client_id="Iv23liNmVnxkNuRfG8tr",
        client_secret="a34898f8a21ee70c7516948a3f59708ae29281ac"
    )

    # Store config in keyring
    if store_github_app_config_in_keyring(config):
        print("GitHub App configuration stored in system keyring.")
    else:
        print("Failed to store GitHub App configuration in system keyring.")
        sys.exit(1)

    # Test getting an installation token
    owner = "Arc-Computer"
    repo = "arc-memory"
    token = get_installation_token_for_repo(owner, repo)

    if token:
        print(f"Successfully obtained installation token for {owner}/{repo}")
        print(f"Token: {token[:10]}...")
    else:
        print(f"Failed to get installation token for {owner}/{repo}")

if __name__ == "__main__":
    main()
