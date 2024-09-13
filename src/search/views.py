from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import os

from .models import SearchRequest, SearchResponse, SearchResult, FileContext, SpanInfo
from .search import search_code, search_cluster, answer

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.repo.service import get_no_auth
from src.config import REPOS_ROOT, INDEX_ROOT
from codesearch.moatless import FileRepository
from codesearch.moatless.workspace import Workspace
from src.index import get_or_create_index

search_router = APIRouter()

@search_router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate that the repo exists
    repo = get_no_auth(db_session=db_session, repo_name=request.repo_name)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Set up the search environment
    repo_dir = os.path.join(REPOS_ROOT, request.repo_name)
    persist_dir = os.path.join(INDEX_ROOT, request.repo_name)
    file_repo = FileRepository(repo_path=repo_dir)
    code_index = get_or_create_index(request.repo_name, {})
    workspace = Workspace(file_repo=file_repo, code_index=code_index)

    # Perform the search
    code_results = search_code(request.query, code_index, workspace)
    # cluster_results = search_cluster(request.query, code_index, workspace)

    # Format the results
    def format_results(results) -> List[str]:
        span_set = ""
        for f, v in results:
            print("[File]: ", f)
            span_set += v.to_prompt() + "\n"
            # for span in [span.span_id for span in v.spans]:
            #     span_set.append(span)
            #     print(span)
        return span_set

    result = format_results(code_results)
    a = await answer(request.query, result)

    # search_result = SearchResult(
    #     code_results=format_results(code_results),
    #     # cluster_results=format_results(cluster_results)
    # )


    return JSONResponse(content={"answer": a})

# Don't forget to include this router in your main FastAPI app
# app.include_router(search_router)