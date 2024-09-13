from cowboy_lib.coverage import TestCoverage

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import Field, root_validator

from src.models import RTFSBase
from src.database.core import Base
from src.config import Language
from src.auth.models import User

import re
from typing import List


class Repo(Base):
    """
    Stores configuration for a repository
    """

    __tablename__ = "repos"

    id = Column(Integer, primary_key=True)
    repo_name = Column(String)
    url = Column(String)
    language = Column(String)
    repo_size = Column(Integer)
    views = Column(Integer)

    # remote = Column(String)
    # main = Column(String)
    # language = Column(String)

    users = relationship("User", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            # "repo_name": self.repo_name,
            "url": self.url,
        }


class RepoBase(RTFSBase):
    url: str


class RepoGet(RepoBase):
    pass


class RepoCreate(RepoBase):
    url: str

    @root_validator(pre=True)
    def validate_url(cls, values):
        url = values.get("url")
        if not url:
            raise ValueError("URL is required")

        # Validate GitHub URL format
        github_http_pattern = r"^https?://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$"
        github_ssh_pattern = r"^git@github\.com:[\w.-]+/[\w.-]+(?:\.git)?$"

        if not (
            re.match(github_http_pattern, url) or re.match(github_ssh_pattern, url)
        ):
            raise ValueError(
                "Invalid GitHub URL format. Must be either HTTP(S) or SSH form."
            )

        return values


class RepoList(RTFSBase):
    user_repos: List[RepoBase]
    recommended_repos: List[RepoBase]


class RepoRemoteCommit(RTFSBase):
    sha: str


class PrivateRepoAccess(Exception):
    pass
