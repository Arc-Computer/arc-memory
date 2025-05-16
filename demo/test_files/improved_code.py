
import os
import sys
import time
import json
import csv
from typing import List, Dict, Any, Optional
import logging

# Configuration class
class Config:
    def __init__(self, api_url='https://api.example.com', timeout=30, retries=3):
        self.api_url = api_url
        self.timeout = timeout
        self.retries = retries

config = Config()

# Logger setup
logging.basicConfig(level=logging.DEBUG)

# Utility functions
def read_data(file_path: str) -> Any:
    try:
        with open(file_path, 'r') as file:
            if file_path.endswith('.json'):
                return json.load(file)
            else:
                return file.readlines()
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        raise

def save_results(results: List[Dict], output_file: str, format: str) -> None:
    try:
        if format == 'json':
            with open(output_file, 'w') as f:
                json.dump(results, f)
        elif format == 'csv':
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
    except Exception as e:
        logging.error(f"Error saving results: {e}")
        raise

def process_data(data: List[Dict]) -> List[Dict]:
    results = []
    for item in data:
        if isinstance(item, dict) and item.get('value', 0) > 0:
            item['processed'] = True
            item['timestamp'] = time.time()
            results.append(item)
    return results

class DataProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.results = []
        self.errors = []

    def process_item(self, item: Any) -> Optional[Dict]:
        try:
            if isinstance(item, str):
                item = json.loads(item)
            if 'value' in item and item['value'] > 0:
                item['processed'] = True
                item['timestamp'] = time.time()
                self.results.append(item)
                return item
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid item: {item}")
            return None

    def get_results(self) -> List[Dict]:
        return self.results

    def get_errors(self) -> List[str]:
        return self.errors

def main():
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    format = sys.argv[3] if len(sys.argv) > 3 else 'json'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    data = read_data(data_file)
    results = process_data(data)
    output_file = os.path.join(output_dir, f'results.{format}')
    save_results(results, output_file, format)

    processor = DataProcessor(config)
    additional_items = [{"value": 10, "name": "Item 1"}, {"value": 20, "name": "Item 2"}, {"value": -5, "name": "Item 3"}]
    for item in additional_items:
        processor.process_item(item)

    processor_results = processor.get_results()
    logging.info(f"Processor processed {len(processor_results)} items")
    errors = processor.get_errors()
    if errors:
        logging.error(f"Processor encountered {len(errors)} errors")

if __name__ == '__main__':
    main()
