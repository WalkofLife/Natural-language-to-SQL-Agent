"""
Purpose:
- request context
- request ID propagation
- timing
"""

import uuid
import time
from contextvars import ContextVar

# ContextVar allows request-scoped values.
# Each HTTP request gets its own request_id
# even if multiple requests execute concurrently.
_request_id = ContextVar("request_id", default=None)

def generate_request_id():
    """Generate globally unique request IDs.
    Example: req_a12f23f..."""
    return f"req_{uuid.uuid4().hex}"

def set_request_id(request_id: str):
    """Stores request ID for the current execution context.
    This allows:
    - logger
    - MLFlow
    - service layer
    
    to access the same ID without passing it manually."""
    _request_id.set(request_id)
    
def get_request_id():
    """Retrieve request ID anywhere in code"""
    return _request_id.get() or "unknown"

    