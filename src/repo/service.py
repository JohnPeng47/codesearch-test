from src.auth.models import User
from src.queue.core import TaskQueue
from src.queue.service import enqueue_task_and_wait

from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT

from .repository import GitRepo, PrivateRepoError
from .models import Repo, RepoCreate, PrivateRepoAccess, repo_ident
from .tasks import InitIndexGraphTask

import shutil
from typing import List, Tuple
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)


def start_indexing(
    task_queue: TaskQueue,
    user: User,
    repo_dst: str,
    index_persist_dir: str,
    save_graph_path: str,
) -> InitIndexGraphTask:
    task = InitIndexGraphTask(
        task_args={
            "repo_dst": repo_dst,
            "index_persist_dir": index_persist_dir,
            "save_graph_path": save_graph_path,
        }
    )
    enqueue_task_and_wait(task_queue=task_queue, user_id=user.id, task=task)


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


def create_or_find(
    *, db_session, curr_user: User, repo_in: RepoCreate, task_queue: TaskQueue
) -> str:
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

        # TODO: add error logging
        task = InitIndexGraphTask(
            task_args={
                "repo_dst": repo_dst,
                "index_persist_dir": index_persist_dir,
                "save_graph_path": save_graph_path,
            }
        )
        enqueue_task_and_wait(task_queue=task_queue, user_id=curr_user.id, task=task)

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

        return task.task_id

    except PrivateRepoError as e:
        raise PrivateRepoAccess

    # TODO: think
    except Exception as e:
        db_session.rollback()

        GitRepo.delete_repo(repo_dst)
        logger.error(f"Failed to create repo configuration: {e}")

        raise e
