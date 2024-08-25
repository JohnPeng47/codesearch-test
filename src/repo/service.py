from src.auth.models import User
from src.config import REPOS_ROOT
from src.queue.core import TaskQueue
from src.index import get_or_create_index

from .repository import GitRepo, PrivateRepoError
from .models import Repo, RepoCreate, PrivateRepoAccess

from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)

def get_no_auth(*, db_session, repo_name: str) -> Repo:
    """Returns a repo if it exists for any user"""
    return (
        db_session.query(Repo)
        .filter(Repo.repo_name == repo_name)
        .one_or_none()
    )

def get_auth(*, db_session, curr_user: User, repo_name: str) -> Repo:
    """Returns a repo if it exists for the current user"""
    return (
        db_session.query(Repo)
        .filter(Repo.repo_name == repo_name, curr_user in Repo.users)
        .one_or_none()
    )

def delete(*, db_session, curr_user: User, repo_name: str) -> Repo:
    """Deletes a repo based on the given repo name."""

    repo = get_auth(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    if repo:
        repo.users.remove(curr_user)
        if repo.users.count() == 0:
            print("No more users, deleting repo")
            GitRepo.delete_repo(Path(REPOS_ROOT) / repo_name)

        db_session.delete(repo)
        db_session.commit()

        return repo
    
    return None

# def list(*, db_session, curr_user: User) -> Repo:
#     """Lists all repos for a user."""

#     return db_session.query(Repo).filter(curr_user.id in Repo.users).all()

async def create_or_find(
    *,
    db_session,
    curr_user: User,
    repo_in: RepoCreate,
    task_queue: TaskQueue,
) -> Repo:
    """Creates a new repo or returns an existing repo if we already have it downloaded"""
    repo = get_no_auth(
        db_session=db_session, repo_name=repo_in.repo_name
    )
    if repo:
        return repo

    repo_dst = None
    try:
        repo_dst = Path(REPOS_ROOT) / repo_in.repo_name
        git_repo = GitRepo.clone_repo(repo_dst, repo_in.url)
        
        # store the repo in the index
        get_or_create_index(repo_in.repo_name, {})
        
        lang, sz = git_repo.get_lang_and_size()
        repo = Repo(
            **repo_in.dict(),
            users=curr_user,
            language=lang,
            repo_size=sz
        )

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