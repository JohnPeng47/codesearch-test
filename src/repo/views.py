from cowboy_lib.repo import GitRepo

from src.database.core import get_db
from src.auth.service import get_current_user
from src.auth.models import User
from src.queue.core import get_queue, TaskQueue
from src.queue.models import TaskResponse
from src.queue.service import enqueue_task
from src.exceptions import ClientActionException
from src.models import HTTPSuccess
from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT

from .service import list_repos, delete, get_repo
from .repository import GitRepo, PrivateRepoError
from .models import (
    Repo,
    RepoCreate,
    RepoListResponse,
    RepoResponse,
    RepoDeleteRequest,
    RepoSummarizeRequest,
    repo_ident,
)
from .tasks import InitIndexGraphTask
from .graph import summarize

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from logging import getLogger

logger = getLogger(__name__)


repo_router = APIRouter()


def http_to_ssh(url):
    """Convert HTTP(S) URL to SSH URL."""
    match = re.match(r"https?://(?:www\.)?github\.com/(.+)/(.+)\.git", url)
    if match:
        return f"git@github.com:{match.group(1)}/{match.group(2)}.git"
    return url  # Return original if not a GitHub HTTP(S) URL


# @repo_router.post("/repo/create", response_model=RepoResponse)
@repo_router.post("/repo/create")
async def create_repo(
    repo_in: RepoCreate,
    db_session: Session = Depends(get_db),
    curr_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    try:
        existing_repo = get_repo(
            db_session=db_session,
            curr_user=curr_user,
            owner=repo_in.owner,
            repo_name=repo_in.repo_name,
        )
        if existing_repo:
            if curr_user not in existing_repo.users:
                # add mapping between user and existing repo
                existing_repo.users.append(curr_user)
                db_session.add(existing_repo)
                db_session.commit()

            return RepoResponse(
                owner=existing_repo.owner, repo_name=existing_repo.repo_name
            )

        repo_dst = None
        index_persist_dir = INDEX_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        repo_dst = REPOS_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        save_graph_path = GRAPH_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)

        git_repo = GitRepo.clone_repo(repo_dst, repo_in.url)

        # TODO: add error logging
        task = InitIndexGraphTask(
            task_args={
                "repo_dst": repo_dst,
                "index_persist_dir": index_persist_dir,
                "save_graph_path": save_graph_path,
            }
        )
        enqueue_task(task_queue=task_queue, user_id=curr_user.id, task=task)

        # TODO: should maybe turn this into task as well
        # would need asyncSession to perform db_updates though
        lang, sz = git_repo.get_lang_and_size()
        repo = Repo(
            **repo_in.dict(),
            language=lang,
            repo_size=sz,
            file_path=str(repo_dst),
            index_path=str(index_persist_dir),
            graph_path=str(save_graph_path),
            users=[curr_user],
        )

        db_session.add(repo)
        db_session.commit()

        # print("TASKID: ", task.task_id, "STATUS: ", task.status)
        # need as_dict to convert cloned_folders to list
        return RepoResponse(owner=repo.owner, repo_name=repo.repo_name)

    except PrivateRepoError as e:
        raise ClientActionException(message="Private repo not yet supported", ex=e)

    # TODO: think
    except Exception as e:
        db_session.rollback()

        GitRepo.delete_repo(repo_dst)
        logger.error(f"Failed to create repo configuration: {e}")

        raise e


@repo_router.get("/repo/list", response_model=RepoListResponse)
def get_user_and_recommended_repos(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user, recommended = list_repos(db_session=db_session, curr_user=current_user)
    return RepoListResponse(
        user_repos=[
            RepoResponse(repo_name=repo.repo_name, owner=repo.owner) for repo in user
        ],
        recommended_repos=[
            RepoResponse(repo_name=recommended.repo_name, owner=recommended.owner)
            for recommended in recommended
        ],
    )


# TODO: should really
@repo_router.post("/repo/summarize")
async def summarize_repo(
    request: RepoSummarizeRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    repo = get_repo(
        db_session=db_session,
        curr_user=current_user,
        owner=request.owner,
        repo_name=request.repo_name,
    )
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    summarized = summarize(repo.file_path, repo.graph_path)
    return summarized


@repo_router.post("/repo/delete")
async def delete_repo(
    request: RepoDeleteRequest,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_queue: TaskQueue = Depends(get_queue),
):
    deleted = delete(
        db_session=db_session,
        curr_user=current_user,
        owner=request.owner,
        repo_name=request.repo_name,
    )
    if not deleted:
        raise HTTPException(
            status_code=400, detail="A repo with this name does not exist."
        )

    return HTTPSuccess()


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
