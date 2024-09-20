from .models import Task, TaskStatus

from fastapi import Request
from threading import Lock
from collections import defaultdict
from typing import List, Dict, Callable
from concurrent.futures import ThreadPoolExecutor


class TaskQueue:
    """
    A set of queues separated by user_id
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            print("Creating new TaskQueue instance")
            cls._instance = super(TaskQueue, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Initialize instance variables only once
            self.queue: Dict[str, List[Task]] = defaultdict(list)
            self.locks = defaultdict(list)
            self.executor = ThreadPoolExecutor(
                max_workers=5
            )  # Adjust max_workers as needed
            self._initialized = True  # Mark as initialized

    def _acquire_lock(self, user_id: int):
        if self.locks.get(user_id, None) is None:
            self.locks[user_id] = Lock()
        return self.locks.get(user_id)

    def put(self, user_id: int, task: Task):
        with self._acquire_lock(user_id):
            self.queue[user_id].append(task)
            self.executor.submit(
                self._execute_and_complete,
                task.task,
                user_id,
                task.task_id,
                task.task_args,
            )

    def _execute_and_complete(
        self, task: Callable, user_id: int, task_id: str, task_args: Dict
    ):
        print(f"Executing task {task_id} for with {task_args}")
        res = task(**task_args)

        with self._acquire_lock(user_id):
            for i in range(len(self.queue[user_id])):
                if self.queue[user_id][i].task_id == task_id:
                    t = self.queue[user_id].pop(i)
                    t.result = res

    def get_all(self, user_id: int) -> List[Task]:
        if len(self.queue[user_id]) == 0:
            return []

        tasks = []
        for t in filter(
            lambda t: t.status == TaskStatus.PENDING.value, self.queue[user_id]
        ):
            t.status = TaskStatus.STARTED.value
            tasks.append(t.task)

        return tasks

    def peak(self, user_id: int, n: int) -> List[Task]:
        """
        Get the first n tasks in queue without removing
        """
        if len(self.queue[user_id]) == 0:
            return []

        return [t.task for t in self.queue[user_id][:n]]


def get_queue(request: Request):
    return request.state.task_queue


def get_token_registry(request: Request):
    from main import token_registry

    return token_registry


def get_token(request: Request):
    """
    Returns the user id
    """
    token = request.headers.get("x-task-auth", None)
    # need this or else we end up converting None to "None" **shakes fist @ python moment"
    return str(token) if token else None
