#!/usr/bin/env python3
"""
Self-Healing Code Generation Loop Demo

This script demonstrates how to use the self-healing code generation loop
to automatically improve code quality. It runs the loop on a sample code file
and shows the improvements made.

Usage: python run_self_healing_demo.py
"""

import os
import sys
import argparse
import colorama
from colorama import Fore, Style
from pathlib import Path

# Initialize colorama for cross-platform colored terminal output
colorama.init()

def main():
    """Main entry point for the demo."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Self-Healing Code Generation Loop Demo")
    parser.add_argument("--repo", default=".", help="Path to the repository (default: current directory)")
    parser.add_argument("--file", default="demo/test_files/sample_code.py", help="File to improve (default: demo/test_files/sample_code.py)")
    parser.add_argument("--iterations", type=int, default=2, help="Maximum number of iterations (default: 2)")
    parser.add_argument("--threshold", type=float, default=0.7, help="Improvement threshold (default: 0.7)")
    parser.add_argument("--output", default="demo/test_files/improved_code.py", help="Output file for improved code (default: demo/test_files/improved_code.py)")

    args = parser.parse_args()

    # Get the absolute path to the self-healing loop script
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    self_healing_script = os.path.join(script_dir, "agents", "self_healing_loop.py")

    # Check if the script exists
    if not os.path.exists(self_healing_script):
        print(f"{Fore.RED}Error: Self-healing loop script not found at {self_healing_script}{Style.RESET_ALL}")
        print(f"{Fore.RED}Make sure you're running this script from the correct directory.{Style.RESET_ALL}")
        sys.exit(1)

    # Check if the file to improve exists
    if not os.path.exists(args.file):
        print(f"{Fore.RED}Error: File to improve not found at {args.file}{Style.RESET_ALL}")
        sys.exit(1)

    # Print welcome message
    print(f"{Fore.GREEN}=== Self-Healing Code Generation Loop Demo ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}This demo will run the self-healing loop on {args.file}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}The improved code will be saved to {args.output}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Maximum iterations: {args.iterations}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Improvement threshold: {args.threshold}{Style.RESET_ALL}")
    print()

    # Build the command to run the self-healing loop
    command = [
        sys.executable,
        self_healing_script,
        "--repo", args.repo,
        "--file", args.file,
        "--iterations", str(args.iterations),
        "--threshold", str(args.threshold),
        "--output", args.output
    ]

    # Print the command
    print(f"{Fore.BLUE}Running command: {' '.join(command)}{Style.RESET_ALL}")
    print()

    # Run the command
    import subprocess
    try:
        subprocess.run(command, check=True)

        # Check if the output file was created
        if os.path.exists(args.output):
            print(f"\n{Fore.GREEN}Demo completed successfully!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Improved code saved to {args.output}{Style.RESET_ALL}")

            # Compare the original and improved code
            print(f"\n{Fore.CYAN}=== Code Comparison ==={Style.RESET_ALL}")

            # Get the original and improved code
            with open(args.file, 'r') as f:
                original_code = f.read()

            with open(args.output, 'r') as f:
                improved_code = f.read()

            # Calculate the difference in line count
            original_lines = len(original_code.splitlines())
            improved_lines = len(improved_code.splitlines())
            line_diff = improved_lines - original_lines

            print(f"{Fore.CYAN}Original code: {original_lines} lines{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Improved code: {improved_lines} lines{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Difference: {line_diff:+d} lines{Style.RESET_ALL}")

            # Suggest next steps
            print(f"\n{Fore.GREEN}=== Next Steps ==={Style.RESET_ALL}")
            print(f"1. Review the improved code in {args.output}")
            print(f"2. Run tests to ensure the improved code works correctly")
            print(f"3. Commit the changes if you're satisfied with the improvements")
            print(f"4. Try the self-healing loop on other files in your codebase")
        else:
            print(f"\n{Fore.RED}Error: Output file not created.{Style.RESET_ALL}")

    except subprocess.CalledProcessError as e:
        print(f"\n{Fore.RED}Error running self-healing loop: {e}{Style.RESET_ALL}")
        print(f"stdout: {e.stdout.decode('utf-8') if e.stdout else ''}")
        print(f"stderr: {e.stderr.decode('utf-8') if e.stderr else ''}")

    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
