from pydantic import BaseModel, Field
from typing import Any

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    
class QueryResponse(BaseModel):
    sql: str
    results: list[Any]
    success: bool
    latency_ms: int