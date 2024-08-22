from src.utils import gen_random_name
from src.auth.models import User
from src.config import REPOS_ROOT
from src.queue.core import TaskQueue

from .repository import GitRepo, PrivateRepoError
from .models import Repo, RepoCreate, PrivateRepoAccess

from pathlib import Path
from logging import getLogger
from fastapi import HTTPException


logger = getLogger(__name__)

# Return GitRepo here
def get(*, db_session, repo_name: str) -> Repo:
    """Returns a repo based on the given repo name."""
    return (
        db_session.query(Repo)
        .filter(Repo.repo_name == repo_name)
        .one_or_none()
    )

def delete(*, db_session, curr_user: User, repo_name: str) -> Repo:
    """Deletes a repo based on the given repo name."""

    repo = get(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    if repo:
        db_session.delete(repo)
        db_session.commit()

        GitRepo.delete_repo(Path(repo.source_folder))
        return repo

    return None

def list(*, db_session, curr_user: User) -> Repo:
    """Lists all repos for a user."""

    return db_session.query(Repo).filter(Repo.user_id == curr_user.id).all()


async def create_or_find(
    *,
    db_session,
    curr_user: User,
    repo_in: RepoCreate,
    task_queue: TaskQueue,
) -> Repo:
    """Creates a new repo or returns an existing repo if we already have it downloaded"""
    repo = get(
        db_session=db_session, repo_name=repo_in.repo_name
    )
    if repo:
        return repo

    repo_dst = None
    try:
        repo = Repo(
            **repo_in.dict(),
            users=curr_user
        )

        repo_dst = Path(REPOS_ROOT) / repo.repo_name / gen_random_name()
        GitRepo.clone_repo(repo_dst, repo.url)

        db_session.add(repo)
        db_session.commit()

        return repo

    except PrivateRepoError as e:
        raise PrivateRepoAccess

    except Exception as e:
        db_session.rollback()
        if repo:
            delete(db_session=db_session, repo_name=repo.repo_name)

        if repo_dst:
            GitRepo.delete_repo(repo_dst)

        logger.error(f"Failed to create repo configuration: {e}")
        raise