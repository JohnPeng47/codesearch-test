from pathlib import Path
import os
from typing import Dict, List
import mimetypes
import fnmatch
from pathlib import Path
import json

from codesearch.moatless.index import CodeIndex
from codesearch.moatless.index.epic_split import EpicSplitter
from codesearch.moatless.index.settings import IndexSettings


def get_or_create_index(file_repo, persist_dir, cluster_json) -> CodeIndex:
    """
    Gets or creates the code embeddings/docstore for the repo
    """

    index_settings = IndexSettings(embed_model="text-embedding-3-small")

    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        print("Load from disk")
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
        nodes = code_index.run_ingestion()
        code_index.persist(persist_dir)

    return code_index
