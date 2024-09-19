from src.auth.models import User
from src.config import REPOS_ROOT
from src.queue.core import TaskQueue

from .repository import GitRepo, PrivateRepoError
from .models import Repo, RepoCreate, PrivateRepoAccess

import re
from typing import List, Tuple
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)

def extract_gh_url(url):
    http_pattern = r'https?://github\.com/([^/]+)/([^/]+)\.git'
    ssh_pattern = r'git@github\.com:([^/]+)/([^/]+)\.git'
    
    # Try matching HTTP(S) pattern
    http_match = re.match(http_pattern, url)
    if http_match:
        return http_match.groups()
    
    # Try matching SSH pattern
    ssh_match = re.match(ssh_pattern, url)
    if ssh_match:
        return ssh_match.groups()
    
    return None, None

def get_no_auth(*, db_session, gh_url: str) -> Repo:
    """Returns a repo if it exists for any user"""
    return db_session.query(Repo).filter(Repo.url == gh_url).one_or_none()


def get_auth(*, db_session, curr_user: User, gh_url: str) -> Repo:
    """Returns a repo if it exists for the current user"""
    return (
        db_session.query(Repo)
        .filter(Repo.url == gh_url, curr_user in Repo.users)
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


def list_repos(*, db_session, curr_user: User) -> Tuple[List[Repo], List[Repo]]:
    """
    Lists all the repos on the user's frontpage
    """
    recommended_repos = (
        db_session.query(Repo)
        .order_by(Repo.views.desc())
        .all()
    )
    user_repos = db_session.query(Repo).filter(Repo.users.contains(curr_user)).all()
    return user_repos, recommended_repos

async def create_or_find(
    *,
    db_session,
    curr_user: User,
    repo_in: RepoCreate,
    task_queue: TaskQueue,
) -> Repo:
    """Creates a new repo or returns an existing repo if we already have it downloaded"""
    repo = get_no_auth(db_session=db_session, gh_url=repo_in.url)
    if repo:
        print("Old repo users: ", repo.users)
        if curr_user not in repo.users:
            # add mapping between user and existing repo
            repo.users.append(curr_user)
            db_session.add(repo)
            db_session.commit()
            
        return repo

    repo_dst = None
    try:
        print("Creating new repo")
        repo_dst = Path(REPOS_ROOT) / (repo_in.owner + "_" + repo_in.repo_name)
        git_repo = GitRepo.clone_repo(repo_dst, repo_in.url)

        # store the repo in the index
        # get_or_create_index(repo_name, {})

        lang, sz = git_repo.get_lang_and_size()
        repo = Repo(**repo_in.dict(), language=lang, repo_size=sz, file_path=str(repo_dst), users=[curr_user])

        db_session.add(repo)
        db_session.commit()

        return repo

    except PrivateRepoError as e:
        raise PrivateRepoAccess

    # QUESTION: do we need to explicitly delete the record here?
    except Exception as e:
        print("Handling deleting: ", e)
        db_session.rollback()
        if repo:
            delete(db_session=db_session, repo_name=repo_in.repo_name)

        if repo_dst:
            GitRepo.delete_repo(repo_dst)

        logger.error(f"Failed to create repo configuration: {e}")
        raise
