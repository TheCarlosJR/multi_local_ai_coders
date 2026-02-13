"""
Structured Logging with Context Propagation

Uses structlog for structured, contextual logging.
Exports logs to:
- Console (pretty printed)
- JSON files (for log aggregation)
- OpenTelemetry traces

Installation:
    pip install structlog python-json-logger
"""

import logging
import logging.handlers
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

# Context variables for distributed tracing
trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
service_name: ContextVar[str] = ContextVar('service_name', default='ai-coders')


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context variables
        if tid := trace_id.get():
            log_data['trace_id'] = tid
        if sid := span_id.get():
            log_data['span_id'] = sid
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class StructuredLogger:
    """Structured logging setup."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        level: int = logging.INFO,
        enable_json: bool = True,
        enable_console: bool = True,
    ):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Root logger setup
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler (human-readable)
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # JSON file handler (machine-readable)
        if enable_json:
            json_file = self.log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            json_handler = logging.FileHandler(json_file)
            json_handler.setLevel(logging.DEBUG)  # Capture all levels in JSON
            json_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(json_handler)
        
        # Setup structlog if available
        if STRUCTLOG_AVAILABLE:
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,
            )
        
        self.logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def set_trace_context(trace_id_val: str, span_id_val: Optional[str] = None):
    """Set distributed tracing context."""
    trace_id.set(trace_id_val)
    if span_id_val:
        span_id.set(span_id_val)


def clear_trace_context():
    """Clear distributed tracing context."""
    trace_id.set(None)
    span_id.set(None)


class LogContext:
    """Context manager for logging context."""
    
    def __init__(self, **extra):
        self.extra = extra
        self.logger = get_logger(__name__)
    
    def __enter__(self):
        # Store extra fields in thread-local storage (would need structlog context in production)
        return self
    
    def __exit__(self, *args):
        pass
