"""Pytest configuration file."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# For CI environments, we need to handle the case when there's no .env file
# GitHub Actions sets GITHUB_TOKEN automatically, so we can use that
if "GITHUB_TOKEN" not in os.environ and "GITHUB_ACTIONS" in os.environ:
    # In GitHub Actions, the GITHUB_TOKEN is available as a secret
    # and is automatically set in the environment
    print("Running in GitHub Actions environment, using GITHUB_TOKEN from secrets")

    # If we're in CI and there's no GITHUB_TOKEN, we can skip GitHub tests
    if "GITHUB_TOKEN" not in os.environ:
        print("No GITHUB_TOKEN found in environment, GitHub tests will be skipped")

        # We can also set a dummy token to avoid errors in tests that expect a token
        # but will be skipped due to the pytestmark
        os.environ["GITHUB_TOKEN"] = "dummy_token_for_skipped_tests"
