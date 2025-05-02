"""Utilities for enhanced logging in simulation.

This module provides utilities for capturing detailed logs during simulation
and storing them for later analysis.
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from arc_memory.logging_conf import get_logger

logger = get_logger(__name__)


class SimulationLogger:
    """Logger for capturing detailed simulation information.
    
    This class provides methods for capturing and storing detailed logs
    during simulation execution, including commands run, outputs, errors,
    and metrics collected.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the simulation logger.
        
        Args:
            output_dir: Directory to store logs (optional)
        """
        self.logs = []
        self.commands = []
        self.metrics = []
        self.errors = []
        self.output_dir = output_dir
        self.start_time = time.time()
        
        logger.info(f"Initialized simulation logger")
        
    def log_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a simulation event.
        
        Args:
            event_type: Type of event (e.g., "info", "command", "metric", "error")
            message: Event message
            details: Additional details (optional)
        """
        timestamp = time.time()
        event = {
            "timestamp": timestamp,
            "relative_time": timestamp - self.start_time,
            "type": event_type,
            "message": message,
            "details": details or {}
        }
        
        self.logs.append(event)
        
        # Also log to the standard logger
        if event_type == "error":
            logger.error(f"Simulation {event_type}: {message}")
            self.errors.append(event)
        elif event_type == "command":
            logger.info(f"Simulation command: {message}")
            self.commands.append(event)
        elif event_type == "metric":
            logger.debug(f"Simulation metric: {message}")
            self.metrics.append(event)
        else:
            logger.info(f"Simulation {event_type}: {message}")
    
    def log_command(self, command: str, output: Optional[str] = None, exit_code: Optional[int] = None) -> None:
        """Log a command execution.
        
        Args:
            command: Command executed
            output: Command output (optional)
            exit_code: Command exit code (optional)
        """
        details = {
            "command": command,
            "output": output,
            "exit_code": exit_code
        }
        
        self.log_event("command", f"Executed: {command}", details)
    
    def log_metric(self, metric_name: str, value: Any) -> None:
        """Log a metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
        """
        details = {
            "metric_name": metric_name,
            "value": value
        }
        
        self.log_event("metric", f"Collected metric: {metric_name}", details)
    
    def log_error(self, error_message: str, exception: Optional[Exception] = None) -> None:
        """Log an error.
        
        Args:
            error_message: Error message
            exception: Exception object (optional)
        """
        details = {
            "error_message": error_message,
            "exception": str(exception) if exception else None
        }
        
        self.log_event("error", error_message, details)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logs.
        
        Returns:
            List of log events
        """
        return self.logs
    
    def get_commands(self) -> List[Dict[str, Any]]:
        """Get command logs.
        
        Returns:
            List of command events
        """
        return self.commands
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get metric logs.
        
        Returns:
            List of metric events
        """
        return self.metrics
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get error logs.
        
        Returns:
            List of error events
        """
        return self.errors
    
    def save_logs(self, file_path: Optional[Path] = None) -> Optional[Path]:
        """Save logs to a file.
        
        Args:
            file_path: Path to save logs (optional)
            
        Returns:
            Path to the saved log file or None if saving failed
        """
        if file_path is None and self.output_dir is not None:
            file_path = self.output_dir / f"simulation_log_{int(self.start_time)}.json"
        
        if file_path is not None:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                log_data = {
                    "start_time": self.start_time,
                    "end_time": time.time(),
                    "duration": time.time() - self.start_time,
                    "logs": self.logs,
                    "commands": self.commands,
                    "metrics": self.metrics,
                    "errors": self.errors
                }
                
                with open(file_path, 'w') as f:
                    json.dump(log_data, f, indent=2)
                
                logger.info(f"Saved simulation logs to {file_path}")
                return file_path
            except Exception as e:
                logger.error(f"Error saving simulation logs: {e}")
                return None
        
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the simulation.
        
        Returns:
            Dictionary with simulation summary
        """
        return {
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration": time.time() - self.start_time,
            "total_logs": len(self.logs),
            "total_commands": len(self.commands),
            "total_metrics": len(self.metrics),
            "total_errors": len(self.errors)
        }
