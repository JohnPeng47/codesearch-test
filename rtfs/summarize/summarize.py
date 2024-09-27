import yaml
from typing import Dict, List
import random

from ..chunk_resolution.graph import (
    ClusterNode,
    NodeKind,
    SummarizedChunk,
    ClusterEdgeKind,
    ClusterEdge,
)
from .lmp import summarize as summarize_llm, categorize_clusters as recategorize_llm
from .lmp import ClusterList

from rtfs.graph import CodeGraph
from rtfs.utils import VerboseSafeDumper
from rtfs.models import OpenAIModel, extract_yaml

SUMMARY_FIRST_PASS = """
The following chunks of code are grouped into the same feature.
I want you to respond with a yaml object that contains the following fields: 
- first come up with a descriptive title that best captures the role that these chunks of code
play in the overall codebase. 
- next, write a short concise but descriptive summary of the chunks, thats 1-2 sentences long
- finally, take a list 4 of important functions/classes as key_variables

Your yaml should take the following format:

title: str
summary: str
key_variables: List[str]

Here is the code:
{code}
"""

REORGANIZE_CLUSTERS = """
You are given a following a set of clusters that encapsulate different features in the codebase. Take these clusters
and group them into logical categories, then come up with a name for each category

Here are some more precise instructions:
1. Carefully read through the entire list of features and functionalities.
2. The categories must be mutually exclusive and collectively exhaustive.
3. Place each feature or functionality under the most appropriate category
4. Each category should not have less than 2 children clusters
5. Make sure you generated name is different from any of the existing Cluster names

Your generated output should only contain the title of your created categories and their list of children titles, without
including any other information such as the children's summary

Return your output in a yaml object, with the following format:

- category: str
    children: []
- category: str
    children: []
- category: str
    children: []
...

{cluster_yaml}
"""


def get_cluster_id():
    return random.randint(1, 10000000)


class LLMException(Exception):
    pass


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
            try:
                summary_data = summarize_llm(child_content).parsed
            except LLMException:
                continue

            print("updating node: ", cluster_id, "with summary: ", summary_data)
            cluster_node = ClusterNode(id=cluster_id, **summary_data.dict())
            self.code_graph.update_node(cluster_node)

    def gen_categories(self):
        try:
            cluster_str, num_clusters = self._clusters_to_yaml()
            clusters: ClusterList = recategorize_llm(cluster_str).parsed

            num_generated_nodes = 0
            for category in clusters.clusters:
                # useless ...
                if not category.children:
                    continue

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
                    num_generated_nodes += 1

            # TODO: this no longer makes sense with clusters being pydantic object
            # if num_clusters != num_generated_nodes:
            #     print("Number of generated nodes does not match number of clusters")
            #     raise LLMException()

        except Exception as e:
            print("Exception: ", e)
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
                        "file_path": child_node.metadata.file_path.replace("\\", "/"),
                    }
                    graph_json["chunks"].append(chunk_info)
                elif child_node.kind == NodeKind.Cluster:
                    graph_json["children"].append(dfs_cluster(child_node))

            return graph_json

        return [dfs_cluster(node) for node in cluster_nodes]

    def _clusters_to_yaml(self):
        # TODO: consider implementing clsuters to json inside Summarizer class
        cluster_nodes = self.code_graph.filter_nodes({"kind": NodeKind.Cluster})
        clusters_json = self._clusters_to_json(cluster_nodes)
        for cluster in clusters_json:
            del cluster["chunks"]
            del cluster["key_variables"]

        return yaml.dump(
            clusters_json,
            Dumper=VerboseSafeDumper,
            sort_keys=False,
        ), len(clusters_json)
