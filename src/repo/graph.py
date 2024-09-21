import os

from moatless.index import CodeIndex
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from rtfs.transforms.cluster import cluster


def create_chunk_graph(code_index: CodeIndex, repo_path: str, graph_path: str):
    nodes = code_index._docstore.docs.values()
    cg = ChunkGraph.from_chunks(repo_path, nodes)

    cg.to_json(graph_path)


def summarize(repo_path: str, graph_path: str):
    cg = ChunkGraph.from_json(repo_path, graph_path)

    cluster(cg)
    summarizer = Summarizer(cg)
    summarizer.summarize()

    print(cg.clusters_to_json())
