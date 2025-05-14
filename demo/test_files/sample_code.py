"""
Sample code file with intentional issues for testing the self-healing code generation loop.
This file contains various code quality issues, inefficient patterns, and potential bugs
that the self-healing loop should identify and fix.
"""

import os
import sys
import time
import json
from typing import List, Dict, Any, Optional

# Global variables (not ideal)
DEBUG = True
config = {"timeout": 30, "retries": 3, "api_url": "https://api.example.com"}

# Function with too many responsibilities and poor error handling
def process_data(data_file, output_dir, format="json", verbose=False):
    """Process data from a file and save results.
    
    Args:
        data_file: Path to input data file
        output_dir: Directory to save output
        format: Output format (json or csv)
        verbose: Whether to print verbose output
    """
    # Print debug information
    if DEBUG:
        print(f"Processing {data_file} in {format} format")
        print(f"Output directory: {output_dir}")
    
    # Check if file exists
    if not os.path.exists(data_file):
        print(f"Error: File {data_file} not found")
        return None
    
    # Read data from file
    try:
        with open(data_file, 'r') as f:
            if data_file.endswith('.json'):
                data = json.load(f)
            else:
                data = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    # Process data
    results = []
    for item in data:
        # Inefficient data processing
        if isinstance(item, dict):
            if 'value' in item and item['value'] > 0:
                item['processed'] = True
                item['timestamp'] = time.time()
                results.append(item)
        else:
            # Try to parse as JSON
            try:
                parsed = json.loads(item)
                if 'value' in parsed and parsed['value'] > 0:
                    parsed['processed'] = True
                    parsed['timestamp'] = time.time()
                    results.append(parsed)
            except Exception:
                # Ignore invalid items
                if verbose:
                    print(f"Ignoring invalid item: {item}")
                continue
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"Error creating output directory: {e}")
            return None
    
    # Save results
    output_file = os.path.join(output_dir, f"results.{format}")
    try:
        if format == "json":
            with open(output_file, 'w') as f:
                json.dump(results, f)
        elif format == "csv":
            # Inefficient CSV writing
            with open(output_file, 'w') as f:
                # Write header
                if results and isinstance(results[0], dict):
                    header = ','.join(results[0].keys())
                    f.write(header + '\n')
                    
                    # Write data
                    for item in results:
                        row = ','.join([str(item.get(key, '')) for key in results[0].keys()])
                        f.write(row + '\n')
        else:
            print(f"Error: Unsupported format {format}")
            return None
    except Exception as e:
        print(f"Error saving results: {e}")
        return None
    
    # Print success message
    if verbose:
        print(f"Successfully processed {len(results)} items")
        print(f"Results saved to {output_file}")
    
    return results

# Class with poor design
class DataProcessor:
    """Class for processing data."""
    
    def __init__(self, config=None):
        """Initialize the data processor.
        
        Args:
            config: Configuration dictionary
        """
        # Use global config if none provided (not ideal)
        self.config = config if config else globals()['config']
        self.results = []
        self.errors = []
        
        # Initialize API connection
        self.api_url = self.config.get('api_url', 'https://api.example.com')
        self.timeout = self.config.get('timeout', 30)
        self.retries = self.config.get('retries', 3)
    
    def process_item(self, item):
        """Process a single item.
        
        Args:
            item: Item to process
            
        Returns:
            Processed item or None if error
        """
        # Duplicate code from process_data function
        if isinstance(item, dict):
            if 'value' in item and item['value'] > 0:
                item['processed'] = True
                item['timestamp'] = time.time()
                self.results.append(item)
                return item
        
        # Try to parse as JSON
        try:
            parsed = json.loads(item)
            if 'value' in parsed and parsed['value'] > 0:
                parsed['processed'] = True
                parsed['timestamp'] = time.time()
                self.results.append(parsed)
                return parsed
        except:
            # Record error
            self.errors.append(f"Invalid item: {item}")
            return None
    
    def get_results(self):
        """Get processing results.
        
        Returns:
            List of processed items
        """
        return self.results
    
    def get_errors(self):
        """Get processing errors.
        
        Returns:
            List of error messages
        """
        return self.errors

# Main function with hardcoded values
def main():
    """Main function."""
    # Hardcoded values
    data_file = "data.json"
    output_dir = "output"
    
    # Process data
    results = process_data(data_file, output_dir, verbose=True)
    
    # Check results
    if results:
        print(f"Processed {len(results)} items")
    else:
        print("Error processing data")
        sys.exit(1)
    
    # Create data processor
    processor = DataProcessor()
    
    # Process additional items
    additional_items = [
        {"value": 10, "name": "Item 1"},
        {"value": 20, "name": "Item 2"},
        {"value": -5, "name": "Item 3"},  # Negative value, should be ignored
    ]
    
    for item in additional_items:
        processor.process_item(item)
    
    # Get results
    processor_results = processor.get_results()
    print(f"Processor processed {len(processor_results)} items")
    
    # Get errors
    errors = processor.get_errors()
    if errors:
        print(f"Processor encountered {len(errors)} errors")

if __name__ == "__main__":
    main()
