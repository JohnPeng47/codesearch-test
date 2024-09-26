import ell
from typing import List
from pydantic import BaseModel

ell.init(
    store="logdir",
    autocommit=True,
)


class CodeSummary(BaseModel):
    title: str
    summary: str
    key_variables: str


@ell.complex(model="gpt-4o-2024-08-06", response_format=CodeSummary)
def summarize(child_content) -> CodeSummary:
    SUMMARY_PROMPT = """
    The following chunks of code are grouped into the same feature.
    I want you to respond with a structured output using the following steps: 
    - first come up with a descriptive title that best captures the role that these chunks of code
    play in the overall codebase. 
    - next, write a short concise but descriptive summary of the chunks, thats 1-2 sentences long
    - finally, take a list 4 of important functions/classes as key_variables (without any explanations!)

    Here is the code:
    {code}
    """
    try:
        return SUMMARY_PROMPT.format(code=child_content)
    except Exception as e:
        raise e


class CodeClusters(BaseModel):
    category: str
    children: List[str]


class ClusterList(BaseModel):
    clusters: List[CodeClusters]


@ell.complex(model="gpt-4o-2024-08-06", response_format=ClusterList)
def categorize_clusters(cluster) -> ClusterList:
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

    Return your output in a structured way
    {cluster}
    """

    try:
        return REORGANIZE_CLUSTERS.format(cluster=cluster)
    except Exception as e:
        raise e
