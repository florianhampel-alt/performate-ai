"""
Centralized logging configuration for the application
"""

import logging
import sys
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for different log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Don't add handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (without colors)
    try:
        file_handler = logging.FileHandler('performate-ai.log')
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, just use console
        logger.warning(f"Could not create file handler: {e}")
    
    return logger


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup global logging configuration
    
    Args:
        level: Default log level
        log_file: Optional log file path
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler for {log_file}: {e}")


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for the current class"""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def log_function_call(func):
    """Decorator to log function calls with arguments and execution time"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = datetime.now()
        
        # Log function call
        func_args = [str(arg) for arg in args]
        func_kwargs = [f"{k}={v}" for k, v in kwargs.items()]
        all_args = func_args + func_kwargs
        args_str = ", ".join(all_args) if all_args else "no args"
        
        logger.debug(f"Calling {func.__name__}({args_str})")
        
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Completed {func.__name__} in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error in {func.__name__} after {execution_time:.3f}s: {str(e)}")
            raise
    
    return wrapper


# Performance monitoring
class PerformanceLogger:
    """Logger for performance monitoring and metrics"""
    
    def __init__(self, name: str):
        self.logger = get_logger(f"perf.{name}")
        self.start_time = None
    
    def start(self, operation: str):
        """Start timing an operation"""
        self.operation = operation
        self.start_time = datetime.now()
        self.logger.info(f"Starting {operation}")
    
    def end(self, additional_info: Optional[str] = None):
        """End timing and log the result"""
        if self.start_time is None:
            self.logger.warning("end() called without start()")
            return
        
        duration = (datetime.now() - self.start_time).total_seconds()
        info_str = f" - {additional_info}" if additional_info else ""
        self.logger.info(f"Completed {self.operation} in {duration:.3f}s{info_str}")
        self.start_time = None
    
    def metric(self, name: str, value: float, unit: str = ""):
        """Log a performance metric"""
        unit_str = f" {unit}" if unit else ""
        self.logger.info(f"METRIC | {name}: {value}{unit_str}")


# Module-level logger for general use
app_logger = get_logger(__name__)
