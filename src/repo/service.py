from src.auth.models import User
from src.queue.core import TaskQueue
from src.index.service import get_or_create_index
from src.graph.service import create_chunk_graph

from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT

from .repository import GitRepo, PrivateRepoError
from .models import Repo, RepoCreate, PrivateRepoAccess, repo_ident

import shutil
from typing import List, Tuple
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)


def get_repo(*, db_session, curr_user: User, owner: str, repo_name: str) -> Repo:
    """Returns a repo if it exists for the current user"""

    # TODO: do we need this?
    existing_user_repo = (
        db_session.query(Repo)
        .filter(
            Repo.owner == owner,
            Repo.repo_name == repo_name,
            Repo.users.contains(curr_user),
        )
        .one_or_none()
    )
    if existing_user_repo:
        return existing_user_repo

    existing_global_repo = (
        db_session.query(Repo)
        .filter(Repo.owner == owner, Repo.repo_name == repo_name)
        .one_or_none()
    )
    return existing_global_repo


def delete(*, db_session, curr_user: User, owner: str, repo_name: str) -> Repo:
    """Deletes a repo based on the given repo name."""

    repo = get_repo(
        db_session=db_session, curr_user=curr_user, owner=owner, repo_name=repo_name
    )
    if repo:
        db_session.delete(repo)
        db_session.commit()

        # if there is only one user of repo then delete the repo
        if len(repo.users) == 1:
            GitRepo.delete_repo(Path(repo.file_path))
            shutil.rmtree(repo.graph_path, ignore_errors=True)
            shutil.rmtree(repo.index_path, ignore_errors=True)

            if repo.summary_path:
                shutil.rmtree(repo.summary_path, ignore_errors=True)

        return repo
    return None


def list_repos(*, db_session, curr_user: User) -> Tuple[List[Repo], List[Repo]]:
    """
    Lists all the repos on the user's frontpage
    """
    recommended_repos = db_session.query(Repo).order_by(Repo.views.desc()).all()
    user_repos = db_session.query(Repo).filter(Repo.users.contains(curr_user)).all()
    return user_repos, recommended_repos


def get_repo_contents(*, db_session, curr_user: User, repo_name: str) -> Repo:
    """
    Returns the contents of a repo
    """
    repo = get_repo(db_session=db_session, curr_user=curr_user, repo_name=repo_name)
    return GitRepo(repo.file_path).to_json()


async def create_or_find(
    *,
    db_session,
    curr_user: User,
    repo_in: RepoCreate,
    task_queue: TaskQueue,
) -> Repo:
    """Creates a new repo or returns an existing repo if we already have it downloaded"""

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

        return existing_repo

    repo_dst = None
    try:
        index_persist_dir = INDEX_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        repo_dst = REPOS_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)
        save_graph_path = GRAPH_ROOT / repo_ident(repo_in.owner, repo_in.repo_name)

        git_repo = GitRepo.clone_repo(repo_dst, repo_in.url)

        # TODO: probably should wrap this in a task
        # TODO: add some error logging altho I think we should defer
        # this to until when we have logging and shit setup
        code_index = get_or_create_index(
            str(repo_dst),
            {},
            persist_dir=str(index_persist_dir),
        )
        create_chunk_graph(code_index, repo_dst, save_graph_path)

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

        return repo

    except PrivateRepoError as e:
        raise PrivateRepoAccess

    # TODO: think
    except Exception as e:
        db_session.rollback()

        GitRepo.delete_repo(repo_dst)
        logger.error(f"Failed to create repo configuration: {e}")

        raise e
