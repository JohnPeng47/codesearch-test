from cowboy_lib.repo import GitRepo

from src.database.core import get_db
from src.auth.service import get_current_user, User
from src.queue.core import get_queue, TaskQueue
from src.exceptions import ClientActionException

from .service import create_or_find, list_repos, delete
from .models import (
    RepoCreate,
    PrivateRepoAccess,
    RepoListResponse,
    RepoResponse,
)

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

repo_router = APIRouter()

def http_to_ssh(url):
    """Convert HTTP(S) URL to SSH URL."""
    match = re.match(r"https?://(?:www\.)?github\.com/(.+)/(.+)\.git", url)
    if match:
        return f"git@github.com:{match.group(1)}/{match.group(2)}.git"
    return url  # Return original if not a GitHub HTTP(S) URL

@repo_router.post("/repo/create", response_model=RepoCreate)
async def create_repo(
    repo_in: RepoCreate,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    try:
        repo_config = await create_or_find(
            db_session=db_session,
            repo_in=repo_in,
            curr_user=current_user,
            task_queue=task_queue,
        )
        # need as_dict to convert cloned_folders to list
        return repo_config.to_dict()
    except PrivateRepoAccess as e:
        raise ClientActionException(message="Private repo not yet supported", ex=e)


@repo_router.get("/repo/list", response_model=RepoListResponse)
def get_user_and_recommended_repos(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user, recommended = list_repos(db_session=db_session, curr_user=current_user)
    print(current_user.email, user, recommended)
    return RepoListResponse(
        user_repos=[RepoResponse(name=repo.repo_name) for repo in user], 
        recommended_repos=[RepoResponse(name=recommended.repo_name) for recommended in recommended]
    )


# @repo_router.delete("/repo/delete/{repo_name}", response_model=HTTPSuccess)
# async def delete_repo(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
#     task_queue: TaskQueue = Depends(get_queue),
# ):
#     deleted = delete(db_session=db_session, repo_name=repo_name, curr_user=current_user)
#     if not deleted:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )

#     # need this to shut down the client after a repo is deleted, or else
#     # it will use old cloned_folders to execute the runner
#     args = RunServiceArgs(user_id=current_user.id, task_queue=task_queue)
#     await shutdown_client(args)

#     return HTTPSuccess()


# @repo_router.delete("/repo/clean/{repo_name}", response_model=HTTPSuccess)
# def clean_repo(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
# ):
#     cleaned = clean(db_session=db_session, repo_name=repo_name, curr_user=current_user)

#     if not cleaned:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )
#     return HTTPSuccess()


# @repo_router.get("/repo/get/{repo_name}", response_model=RepoGet)
# def get_repo(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
# ):
#     repo = get(db_session=db_session, repo_name=repo_name, curr_user=current_user)
#     if not repo:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )
#     return repo.to_dict()

# # TODO: this should return HEAD of repo.source_folder rather than the remote repo
# # once we finish our task refactor
# @repo_router.get("/repo/get_head/{repo_name}", response_model=RepoRemoteCommit)
# def get_head(
#     repo_name: str,
#     db_session: Session = Depends(get_db),
#     current_user: CowboyUser = Depends(get_current_user),
# ):
#     repo = get(db_session=db_session, repo_name=repo_name, curr_user=current_user)
#     if not repo:
#         raise HTTPException(
#             status_code=400, detail="A repo with this name does not exists."
#         )

#     git_repo = GitRepo(Path(repo.source_folder))

#     # return RepoRemoteCommit(sha=git_repo.local_commit)
#     return RepoRemoteCommit(sha=git_repo.remote_commit)
