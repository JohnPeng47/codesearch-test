from pathlib import Path
from typing import List, NamedTuple
from llama_index.core.schema import BaseNode

from rtfs.chunk_resolution.graph import ChunkMetadata
from rtfs_rewrite.ts import cap_ts_queries, TSLangs
from rtfs.cluster.graph import ClusterGraph

import networkx as nx

from .graph import AltChunkNode, AltChunkEdge


class AiderGraph(ClusterGraph):
    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode]):
        graph = cls(repo_path=repo_path, graph=nx.MultiDiGraph(), cluster_roots=[])

        all_chunks = []
        for chunk in chunks:
            definitions = []
            references = []
            for node, capture_name in cap_ts_queries(
                bytearray(chunk.get_content(), encoding="utf-8"), TSLangs.PYTHON
            ):
                match capture_name:
                    case "name.definition.class":
                        definitions.append(node.text.decode())
                    case "name.definition.function":
                        definitions.append(node.text.decode())
                    case "name.reference.call":
                        references.append(node.text.decode())

            node = AltChunkNode(
                id=chunk.node_id,
                og_id=chunk.node_id,
                metadata=ChunkMetadata(**chunk.metadata),
                content=chunk.get_content(),
                # TODO: maybe we should add these fields to CHunkNode
                # definitions=definitions,
                # references=references,
            )

            chunk_node = [
                node,
                {"definitions": definitions, "references": references},
            ]
            all_chunks.append(chunk_node)
            graph.add_node(chunk_node[0])

        # build relation ships
        for c1, refsndefs1 in all_chunks:
            for c2, refsndefs2 in all_chunks:
                for ref in refsndefs1["references"]:
                    if (
                        ref in refsndefs2["definitions"]
                        and c1.id != c2.id
                        and not graph.has_edge(c1.id, c2.id)
                    ):
                        edge = AltChunkEdge(src=c1.id, dst=c2.id, ref=ref)
                        graph.add_edge(edge)

        return graph
