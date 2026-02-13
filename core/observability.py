"""
OpenTelemetry Observability Setup

Provides tracing, metrics, and structured logging.
Without Web UI - exports to:
- Jaeger (local container or cloud)
- Prometheus (for metrics)
- Console (for logs)

Installation:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-jaeger
    pip install opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-sqlalchemy
"""

import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar
from functools import wraps
import time

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)


# Context variables for distributed tracing
request_context: ContextVar[Dict[str, Any]] = ContextVar(
    'request_context',
    default={}
)


class OpenTelemetrySetup:
    """Initialize OpenTelemetry tracing and metrics."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        service_name: str = "multi-local-ai-coders",
        jaeger_host: str = "localhost",
        jaeger_port: int = 6831,
        enabled: bool = True,
    ):
        if not enabled or not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry disabled or unavailable")
            self.enabled = False
            return
        
        self.enabled = True
        self.service_name = service_name
        
        # Setup resource
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "environment": "development",
        })
        
        # Setup Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )
        
        # Setup trace provider
        self.trace_provider = TracerProvider(resource=resource)
        self.trace_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        trace.set_tracer_provider(self.trace_provider)
        
        self.tracer = trace.get_tracer(__name__)
        logger.info(f"✓ OpenTelemetry initialized (Jaeger: {jaeger_host}:{jaeger_port})")
    
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a new span for tracing."""
        if not self.enabled:
            return None
        
        span = self.tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span


class SpanDecorator:
    """Decorator for automatic span creation."""
    
    def __init__(self, span_name: Optional[str] = None):
        self.span_name = span_name
        self.otel = OpenTelemetrySetup()
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            span_name = self.span_name or f"{func.__module__}.{func.__name__}"
            
            if not self.otel.enabled:
                return func(*args, **kwargs)
            
            with self.otel.tracer.start_as_current_span(span_name) as span:
                # Add function arguments as attributes (safe types only)
                for i, arg in enumerate(args[:3]):  # Max 3 positional
                    if isinstance(arg, (str, int, float, bool)):
                        span.set_attribute(f"arg_{i}", str(arg))
                
                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"kwarg_{key}", str(value))
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error", str(e))
                    raise
        
        return wrapper


class TimingDecorator:
    """Decorator for timing function execution."""
    
    def __init__(self, func):
        self.func = func
    
    def __call__(self, *args, **kwargs):
        start = time.time()
        try:
            result = self.func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(f"{self.func.__name__} took {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"{self.func.__name__} failed after {duration:.2f}s: {e}")
            raise


def create_span(name: str, **attributes):
    """Context manager for creating spans."""
    
    otel = OpenTelemetrySetup()
    if not otel.enabled:
        class DummySpan:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def set_attribute(self, key, value): pass
        return DummySpan()
    
    span = otel.tracer.start_span(name)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    
    class SpanContext:
        def __enter__(self):
            return span
        def __exit__(self, *args):
            span.end()
    
    return SpanContext()
