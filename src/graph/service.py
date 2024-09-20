import os

from moatless.index import CodeIndex
from rtfs.chunk_resolution.chunk_graph import ChunkGraph


def create_chunk_graph(
    code_index: CodeIndex,
    repo_path: str = None,
    graph_path: str = None,
):
    nodes = code_index._docstore.docs.values()
    cg = ChunkGraph.from_chunks(repo_path, nodes)

    cg.to_json(graph_path)
