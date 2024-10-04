from pathlib import Path
from typing import List, Dict
from llama_index.core.schema import BaseNode

from rtfs.chunk_resolution.graph import ClusterNode, ChunkNode, ChunkMetadata
from rtfs.graph import CodeGraph, Edge
from rtfs_rewrite.ts import cap_ts_queries, TSLangs

import networkx as nx

from .graph import AltChunkNode, AltChunkEdge


class AiderGraph(CodeGraph):
    def __init__(self, repo_path, g: nx.MultiDiGraph):
        super().__init__(node_types=[ChunkNode, ClusterNode])
        self.repo_path = repo_path
        self._graph = g

    @classmethod
    def from_chunks(cls, repo_path: Path, chunks: List[BaseNode]):
        graph = cls(repo_path, nx.MultiDiGraph())

        all_chunks: List[AltChunkNode] = []
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

            chunk_node = AltChunkNode(
                id=chunk.node_id,
                og_id=chunk.node_id,
                metadata=ChunkMetadata(**chunk.metadata),
                content=chunk.get_content(),
                # TODO: chunkNode cant parse these thet
                definitions=definitions,
                references=references,
            )
            all_chunks.append(chunk_node)
            graph.add_node(chunk_node)

        # build relation ships
        for c1 in all_chunks:
            for c2 in all_chunks:
                for ref in c1.references:
                    if (
                        ref in c2.definitions
                        and c1.id != c2.id
                        and not graph.has_edge(c1.id, c2.id)
                    ):
                        edge = AltChunkEdge(src=c1.id, dst=c2.id, ref=ref)
                        graph.add_edge(edge)

        return graph

    def to_json(self):
        def custom_node_link_data(G):
            data = {
                "directed": G.is_directed(),
                "multigraph": G.is_multigraph(),
                "graph": G.graph,
                "nodes": [],
                "links": [],
            }

            for n, node_data in G.nodes(data=True):
                node_dict = node_data.copy()

                node_dict.pop("references", None)
                node_dict.pop("definitions", None)

                if "metadata" in node_dict and isinstance(
                    node_dict["metadata"], ChunkMetadata
                ):
                    node_dict["metadata"] = node_dict["metadata"].to_json()

                node_dict["id"] = n
                data["nodes"].append(node_dict)

            for u, v, edge_data in G.edges(data=True):
                edge = edge_data.copy()
                edge["source"] = u
                edge["target"] = v
                data["links"].append(edge)

            return data

        graph_dict = {}
        graph_dict["link_data"] = custom_node_link_data(self._graph)

        return graph_dict

    @classmethod
    def from_json(cls, repo_path: Path, json_data: Dict):
        cg = nx.node_link_graph(json_data["link_data"])
        for _, node_data in cg.nodes(data=True):
            if "metadata" in node_data:
                node_data["metadata"] = ChunkMetadata(**node_data["metadata"])

        return cls(repo_path, cg)
