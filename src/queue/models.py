from enum import Enum
from typing import Dict, Optional, Any, Callable
from pydantic import BaseModel, Field, model_validator
from cowboy_lib.api.runner.shared import generate_id
from abc import abstractmethod


class TaskType(str, Enum):
    INIT_GRAPH = "INIT_GRAPH"


class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Task(BaseModel):
    """
    Task datatype
    """

    type: TaskType
    task_id: str = Field(default_factory=lambda: generate_id())
    result: Optional[Any] = Field(default=None)
    status: str = Field(default=TaskStatus.PENDING.value)
    task_args: Optional[Any] = Field(default=None)

    @abstractmethod
    def task(self, **kwargs):
        raise NotImplementedError()


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
