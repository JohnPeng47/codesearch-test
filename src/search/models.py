from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    repo_name: str
    query: str

class SpanInfo(BaseModel):
    span_id: str

class FileContext(BaseModel):
    file_path: str
    spans: List[SpanInfo]

class SearchResult(BaseModel):
    code_results: List[FileContext]
    cluster_results: List[FileContext]

class SearchResponse(BaseModel):
    query: str
    results: SearchResult