from cowboy_lib.coverage import TestCoverage

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pydantic import Field, root_validator

from src.models import RTFSBase
from src.database.core import Base
from src.config import Language
from src.auth.models import User

from typing import List, Any, Dict, Optional


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

    # remote = Column(String)
    # main = Column(String)
    # language = Column(String)

    users = relationship("User", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            # "repo_name": self.repo_name,
            "url": self.url,
        }

class LangConf(RTFSBase):
    """
    Holds the language/framework specific settings
    for a repo
    """

    # currently I expect only an interpreter/compiler path that points
    # to the runtime for the targeted repo
    interp: str


class RepoBase(RTFSBase):
    url: str
    # source_folder: str
    # cloned_folders: List[str]
    # python_conf: PythonConf

    # language: Optional[Language] = Field(default="python")
    # is_experiment: Optional[bool] = Field(default=False)
    # main: Optional[str] = Field(default="main")
    # remote: Optional[str] = Field(default="origin")


class RepoGet(RepoBase):
    pass


class RepoCreate(RepoBase):
    url: str
    repo_name: Optional[str] = Field(None, nullable=True)

    @root_validator(pre=True)
    def set_repo_name(cls, values):
        url = values.get("url", None)
        parts = url.rstrip('/').split('/')
        # stip out .
        parts[1] = parts[1].split(".")[0]
        
        if len(parts) >= 2:
            values["repo_name"] = "_".join(parts)
            return values

        raise ValueError(f"Malformed GH URL: {values['url']}")
        
class RepoList(RTFSBase):
    repo_list: List[RepoBase]

class RepoRemoteCommit(RTFSBase):
    sha: str

class PrivateRepoAccess(Exception):
    pass