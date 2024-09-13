import os
from typing import Dict

from codesearch.moatless.index import CodeIndex
from codesearch.moatless.index.settings import IndexSettings
from codesearch.moatless import FileRepository
from llama_index.core.storage.docstore import SimpleDocumentStore

from rtfs.chunk_resolution.chunk_graph import ChunkGraph
from rtfs.chunk_resolution.summarize import Summarizer
from src.config import REPOS_ROOT, INDEX_ROOT, GRAPH_ROOT


def get_or_create_index(repo_name: str, cluster_json: Dict):
    """
    Gets or creates the code embeddings/docstore for the repo
    """
    repo_path = os.path.join(REPOS_ROOT, repo_name)
    persist_dir = os.path.join(INDEX_ROOT, repo_name)

    file_repo = FileRepository(repo_path)
    index_settings = IndexSettings(embed_model="text-embedding-3-small")

    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        code_index = CodeIndex.from_persist_dir(persist_dir, file_repo=file_repo)
    else:
        code_index = CodeIndex(
            file_repo=file_repo,
            settings=index_settings,
            cluster_list=cluster_json if cluster_json else {},
            use_summaries=False,
            summary_anthropic_model=True,
            summary_ref_vars=False,
        )
        code_index.run_ingestion()
        code_index.persist(persist_dir)

    return code_index


def read_chunks(repo_name: str):
    """
    Reads the chunks from the persist directory
    """
    repo_path = os.path.join(REPOS_ROOT, repo_name)
    persist_dir = os.path.join(INDEX_ROOT, repo_name)

    file_repo = FileRepository(repo_path)
    code_index = CodeIndex.from_persist_dir(persist_dir, file_repo)
    return code_index._docstore.docs.values()


def create_chunk_graph(repo_name: str, summarize: bool = False):
    repo_path = os.path.join(REPOS_ROOT, repo_name)
    persist_dir = os.path.join(INDEX_ROOT, repo_name)
    save_path = os.path.join(GRAPH_ROOT, repo_name)

    nodes = read_chunks(persist_dir, repo_path)
    cg = ChunkGraph.from_chunks(repo_path, nodes)

    cg.cluster()
    
    if summarize:
        summarizer = Summarizer()
        summarizer.summarize(cg, user_confirm=False)
        
    cg.to_json(save_path)

# chunks = create_chunk_graph(
#     Path("tests/repos/index/moatless-tools"),
#     Path("tests/repos/moatless-tools"),
#     "graph.json",
# )