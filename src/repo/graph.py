import os
import json
from pathlib import Path
from enum import Enum
import shutil

from moatless.index import CodeIndex

from src.index.service import get_or_create_index

from rtfs.summarize.summarize import Summarizer
from rtfs.transforms.cluster import cluster
from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.aider_graph.aider_graph import AiderGraph
from src.utils import rm_tree


class GraphType(str, Enum):
    STANDARD = "standard"
    AIDER = "aider"


def get_or_create_chunk_graph(
    code_index: CodeIndex, repo_path: str, graph_path: str, type: GraphType
):
    graph_path = f"{graph_path}_{type}.json"

    nodes = code_index._docstore.docs.values()
    try:
        if os.path.exists(graph_path):
            with open(graph_path, "r") as f:
                graph_dict = json.load(f)

            if type == GraphType.STANDARD:
                cg = ChunkGraph.from_json(Path(repo_path), graph_dict)
            elif type == GraphType.AIDER:
                cg = AiderGraph.from_json(Path(repo_path), graph_dict)
            return cg

        else:
            if type == GraphType.STANDARD:
                cg = ChunkGraph.from_chunks(Path(repo_path), nodes)
            elif type == GraphType.AIDER:
                cg = AiderGraph.from_chunks(repo_path, nodes)

            with open(graph_path, "w") as f:
                json.dump(cg.to_json(), f)

            return cg
    except Exception as e:
        print("EXCEPTION: ", e)
        if os.path.exists(graph_path):
            rm_tree(graph_path)

        raise e


def summarize(
    index_path: str,
    repo_path: str,
    graph_path: str,
    graph_type: GraphType = GraphType.STANDARD,
):
    code_index = get_or_create_index(repo_path, index_path)
    cg = get_or_create_chunk_graph(code_index, repo_path, graph_path, graph_type)

    cluster(cg)

    summarizer = Summarizer(cg)
    summarizer.summarize()
    summarizer.gen_categories()

    # print("Clusters: ", json.dumps(summarizer.clusters_to_json(), indent=2))

    return summarizer.to_json()
