import json
from pathlib import Path

from moatless.index import CodeIndex
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.summarize.summarize import Summarizer
from rtfs.transforms.cluster import cluster


def create_chunk_graph(code_index: CodeIndex, repo_path: str, graph_path: str):
    nodes = code_index._docstore.docs.values()
    cg = ChunkGraph.from_chunks(repo_path, nodes)

    cg.to_json(graph_path)


def summarize(repo_path: str, graph_path: str):
    with open(graph_path, "r") as f:
        graph_dict = json.load(f)

    cg = ChunkGraph.from_json(Path(repo_path), graph_dict)

    cluster(cg)

    summarizer = Summarizer(cg)
    summarizer.summarize()
    summarizer.gen_categories()

    # print("Clusters: ", json.dumps(summarizer.clusters_to_json(), indent=2))

    return summarizer.to_json()
