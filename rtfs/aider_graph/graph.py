import sys

sys.path.append("rtfs_rewrite")

from dataclasses import dataclass, field
from typing import List

from rtfs.chunk_resolution.graph import ChunkNode, ChunkMetadata
from rtfs.graph import CodeGraph, Edge


@dataclass
class AltChunkNode(ChunkNode):
    pass
    # references: List[str] = field(default_factory=list)
    # definitions: List[str] = field(default_factory=list)


@dataclass
class AltChunkEdge(Edge):
    ref: str = field(default="")
