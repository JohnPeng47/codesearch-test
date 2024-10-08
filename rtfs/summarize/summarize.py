import yaml
from typing import Dict, List
import random
import os

from ..chunk_resolution.graph import (
    ClusterNode,
    NodeKind,
    SummarizedChunk,
    ClusterEdgeKind,
    ClusterEdge,
)
from .lmp import (
    summarize as summarize_llm,
    categorize_clusters as recategorize_llm,
    categorize_missing,
)
from .lmp import ClusterList

from rtfs.graph import CodeGraph
from rtfs.utils import VerboseSafeDumper
from rtfs.models import OpenAIModel, extract_yaml
from rtfs.exceptions import LLMValidationError


def get_cluster_id():
    return random.randint(1, 10000000)


class Summarizer:
    def __init__(self, graph: CodeGraph):
        self._model = OpenAIModel()
        self.code_graph = graph

    # TODO: can generalize this to only generating summaries for parent nodes
    # this way we can use generic CodeGraph abstraction
    # OR
    # we can make use of only the edge information -> tag special parent ch
    # actually... this is pointless?

    # TODO: we can parallelize this
    # TODO: reimplement test_run
    def summarize(self):
        for cluster_id, child_content in self._iterate_clusters_with_text():
            summary_data = summarize_llm(child_content).parsed

            print("updating node: ", cluster_id, "with summary: ", summary_data)
            cluster_node = ClusterNode(id=cluster_id, **summary_data.dict())
            self.code_graph.update_node(cluster_node)

    def gen_categories(self):
        """
        Attempts relabel of clusters. If relabel attempt misses any existing clusters, will iteratively
        retry relabeling until all clusters are accounted for.
        """

        def cluster_yaml_str(cluster_nodes):
            clusters_json = self._clusters_to_json(cluster_nodes)
            for cluster in clusters_json:
                cluster.pop("chunks")
                cluster.pop("key_variables")

            return yaml.dump(
                clusters_json,
                Dumper=VerboseSafeDumper,
                sort_keys=False,
            ), [cluster["title"] for cluster in clusters_json]

        retries = 3
        previous_clusters = []
        cluster_yaml, og_clusters = self._clusters_to_yaml(
            self.code_graph.filter_nodes({"kind": NodeKind.Cluster})
        )
        while retries > 0:
            try:
                generated_clusters: ClusterList = (
                    recategorize_llm(cluster_yaml).parsed
                    if retries == 3
                    else categorize_missing(cluster_yaml, previous_clusters).parsed
                )
                generated_child_clusters = []
                for category in generated_clusters.clusters:
                    # why do I still get empty clusters?
                    # useless ...
                    if not category.children:
                        continue

                    cluster_node = self.code_graph.find_node(
                        {"kind": NodeKind.Cluster, "title": category.category}
                    )
                    if not cluster_node:
                        cluster_node = ClusterNode(
                            id=get_cluster_id(),
                            title=category.category,
                            kind=NodeKind.Cluster,
                        )
                        self.code_graph.add_node(cluster_node)

                    for child in category.children:
                        # TODO: consider moving this function from chunkGraph to here
                        child_node = self.code_graph.find_node(
                            {"kind": NodeKind.Cluster, "title": child}
                        )
                        if not child_node:
                            print("Childnode not found: ", child)
                            continue

                        # TODO: should really be using self.code_graph.add_edge
                        self.code_graph._graph.add_edge(
                            child_node.id,
                            cluster_node.id,
                            kind=ClusterEdgeKind.ClusterToCluster,
                        )
                        generated_child_clusters.append(child_node.id)

                # TODO: if more, we dont really care, can prune
                if len(og_clusters) > len(generated_child_clusters):
                    missing = set(og_clusters) - set(generated_child_clusters)
                    raise LLMValidationError(
                        f"Missing clusters from generated categories: {list(missing)}"
                    )
                else:
                    break

            except LLMValidationError as e:
                cluster_yaml, og_clusters = cluster_yaml_str(
                    [self.code_graph.get_node(c) for c in generated_child_clusters]
                )
                previous_clusters = [
                    cluster.category for cluster in generated_clusters.clusters
                ]
                retries -= 1
                if retries == 0:
                    raise Exception("Failed to generate categories")

            except Exception as e:
                raise e

    def to_json(self):
        cluster_nodes = [
            node
            for node in self.code_graph.filter_nodes({"kind": NodeKind.Cluster})
            if len(self.code_graph.parents(node.id)) == 0
        ]

        return self._clusters_to_json(cluster_nodes)

    def _iterate_clusters_with_text(self):
        """
        Concatenates the content of all children of a cluster node
        """
        for cluster in [
            node
            for node, data in self.code_graph._graph.nodes(data=True)
            if data["kind"] == NodeKind.Cluster
        ]:
            child_content = "\n".join(
                [
                    self.code_graph.get_node(c).get_content()
                    for c in self.code_graph.children(cluster)
                    if self.code_graph.get_node(c).kind
                    in [NodeKind.Chunk, NodeKind.Cluster]
                ]
            )
            yield (cluster, child_content)

    def _clusters_to_json(self, cluster_nodes: List[ClusterNode]):
        def dfs_cluster(cluster_node: ClusterNode):
            graph_json = {
                "id": cluster_node.id,
                "title": cluster_node.title,
                "key_variables": cluster_node.key_variables[:4],
                "summary": cluster_node.summary,
                "chunks": [],
                "children": [],
            }

            for child in self.code_graph.children(cluster_node.id):
                child_node = self.code_graph.get_node(child)
                if child_node.kind == NodeKind.Chunk:
                    chunk_info = {
                        "id": child_node.id,
                        "og_id": child_node.og_id,
                        "file_path": child_node.metadata.file_path,
                        # "file_path": os.path.relpath(
                        #     child_node.metadata.file_path, self.code_graph.repo_path
                        # ),
                        "start_line": child_node.range.line_range()[0],
                        "end_line": child_node.range.line_range()[1],
                    }
                    graph_json["chunks"].append(chunk_info)
                elif child_node.kind == NodeKind.Cluster:
                    graph_json["children"].append(dfs_cluster(child_node))

            return graph_json

        return [dfs_cluster(node) for node in cluster_nodes]

    def _clusters_to_yaml(self, cluster_nodes: List[ClusterNode]):
        clusters_json = self._clusters_to_json(cluster_nodes)
        for cluster in clusters_json:
            print(cluster["title"])
            del cluster["chunks"]
            del cluster["key_variables"]

        return yaml.dump(
            clusters_json,
            Dumper=VerboseSafeDumper,
            sort_keys=False,
        ), [cluster["id"] for cluster in clusters_json]
