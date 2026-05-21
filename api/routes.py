from fastapi import APIRouter
from api.schemas import (
    QueryRequest, QueryResponse
)
from services.nl2sql_service import service

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    return service.execute(request.question)
