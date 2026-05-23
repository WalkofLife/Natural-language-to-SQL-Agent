from fastapi import APIRouter, Request
from api.schemas import (
    QueryRequest, QueryResponse
)
from services.nl2sql_service import service

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query(request: Request, body: QueryRequest):
    return service.execute(body.question, request_id = request.state.request_id)
