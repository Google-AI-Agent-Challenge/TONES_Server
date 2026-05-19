from pydantic import BaseModel
from typing import List, Dict, Any


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filter: Dict[str, Any] | None = None


class SearchResultItem(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


class GenerateRequest(BaseModel):
    prompt: str
    context: str | None = None


class GenerateResponse(BaseModel):
    answer: str
