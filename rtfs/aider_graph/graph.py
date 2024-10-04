import sys

sys.path.append("rtfs_rewrite")

from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from src.index.service import get_or_create_chunks

from rtfs.chunk_resolution.graph import ChunkNode, ChunkMetadata
from rtfs.graph import CodeGraph, Edge
from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs_rewrite.fs import RepoFs

from networkx import DiGraph
import networkx as nx
import json


@dataclass
class AltChunkNode(ChunkNode):
    references: List[str] = field(default_factory=[])
    definitions: List[str] = field(default_factory=[])


@dataclass
class AltChunkEdge(Edge):
    ref: str = field(default="")
