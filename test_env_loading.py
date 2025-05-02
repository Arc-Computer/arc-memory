#!/usr/bin/env python
"""Test script to verify environment loading in Smol Agents implementation."""

import os
import sys
from pathlib import Path

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_env_loading")

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_simulation_agent():
    """Test creating a simulation agent."""
    from arc_memory.simulate.workflow import create_simulation_agent
    
    logger.info("Testing simulation agent creation...")
    try:
        agent = create_simulation_agent()
        if agent:
            logger.info("✅ Successfully created simulation agent")
            return True
        else:
            logger.error("❌ Failed to create simulation agent")
            return False
    except Exception as e:
        logger.error(f"❌ Error creating simulation agent: {e}")
        return False

def test_diff_agent():
    """Test creating a diff agent."""
    from arc_memory.simulate.agents.diff_agent import create_diff_agent
    
    logger.info("Testing diff agent creation...")
    try:
        agent = create_diff_agent()
        if agent:
            logger.info("✅ Successfully created diff agent")
            return True
        else:
            logger.error("❌ Failed to create diff agent")
            return False
    except Exception as e:
        logger.error(f"❌ Error creating diff agent: {e}")
        return False

def test_sandbox_agent():
    """Test creating a sandbox agent."""
    from arc_memory.simulate.agents.sandbox_agent import create_sandbox_agent
    
    logger.info("Testing sandbox agent creation...")
    try:
        agent = create_sandbox_agent()
        if agent:
            logger.info("✅ Successfully created sandbox agent")
            return True
        else:
            logger.error("❌ Failed to create sandbox agent")
            return False
    except Exception as e:
        logger.error(f"❌ Error creating sandbox agent: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting environment loading tests")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f".env file exists: {Path('.env').exists()}")
    
    # Check if API keys are already in the environment
    openai_key = os.environ.get("OPENAI_API_KEY")
    e2b_key = os.environ.get("E2B_API_KEY")
    
    logger.info(f"OPENAI_API_KEY in environment: {bool(openai_key)}")
    logger.info(f"E2B_API_KEY in environment: {bool(e2b_key)}")
    
    # Run tests
    results = []
    results.append(("Simulation Agent", test_simulation_agent()))
    results.append(("Diff Agent", test_diff_agent()))
    results.append(("Sandbox Agent", test_sandbox_agent()))
    
    # Print summary
    logger.info("\n--- Test Results Summary ---")
    all_passed = True
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name}: {status}")
        all_passed = all_passed and result
    
    logger.info(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
