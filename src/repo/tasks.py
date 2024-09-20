from src.queue.models import Task, TaskType
from src.index.service import get_or_create_index
from src.graph.service import create_chunk_graph


class InitIndexGraphTask(Task):
    type: TaskType = TaskType.INIT_GRAPH

    def task(self, *, repo_dst, index_persist_dir, save_graph_path):
        code_index = get_or_create_index(
            str(repo_dst),
            {},
            persist_dir=str(index_persist_dir),
        )
        create_chunk_graph(code_index, repo_dst, save_graph_path)
