from moatless.index import CodeIndex, IndexSettings
from moatless import FileRepository
from moatless.workspace import Workspace
from moatless.index.simple_faiss import VectorStoreType
from moatless.codeblocks.module import Module
from moatless.file_context import FileContext

from src.oai import OpenAIModel
from src.config import REPOS_ROOT, INDEX_ROOT, SUMMARIES_ROOT

from pathlib import Path
import os
import json

REPO_NAME = "moatless-tools"
QUERY = """
How is hybrid search combined with semantic search?
"""
queries = [
    "How is the searchresult used in AgenticLoop?",
    "Show me all the places where repomap is used in the code",
    "Explain the different ways that code editing works in aider",
    "How is the unified diff format used by aider?",
    "How does codeParser work?",
]


async def answer(query, code_context):
    good_prompt = """
You are an AI assistant tasked with answering queries about a codebase using provided code contexts. Your goal is to provide a clear, concise, and unified response that directly addresses the query.

Here is the query you need to answer:
{query}

To help you answer this query, you have been provided with relevant code contexts. These contexts are excerpts from the codebase that may contain information pertinent to the query. Here are the code contexts:
{code_context}


Carefully analyze the code contexts provided. Look for information that directly relates to the query. Pay attention to function names, variable declarations, code structure, and comments that might be relevant.

When formulating your response:
1. Focus on answering the query directly, instead of expl   aining the code.
2. Synthesize information from all relevant code contexts to provide a unified answer.
3. Do not comment on individual code contexts separately; instead, integrate the information into a cohesive response.
4. If the query cannot be fully answered with the given information, state what can be determined and what remains unclear.
5. Include relevant snippets of the source code in your response

Start your first sentence by responding to the query directly
""".format(
        query=query,
        code_context=code_context,
    )
    #     bad_prompt = """
    # You are given the following query:
    # {query}

    # Here is the code context:
    # {code_context}

    # Now give an answer to the query based on the code_context provided
    # """.format(query=query, code_context=code_context)

    model = OpenAIModel()
    res = await model.query(good_prompt)
    return res


def read_cluster_file(cluster_file):
    if not cluster_file:
        return {}

    with open(cluster_file, "r") as file:
        data = json.load(file)
    return data


def persist_code_index(file_repo, persist_dir, cluster_json):
    # An OPENAI_API_KEY is required to use the OpenAI Models
    model = "gpt-4o-2024-05-13"
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


def search_code(query: str, code_index: CodeIndex, workspace: Workspace) -> FileContext:
    code_results = code_index.search(query, store_type=VectorStoreType.CODE)
    file_context = workspace.create_file_context(files_with_spans=code_results.hits)

    # Uncomment and modify as needed
    for hit in code_results.hits[:4]:
        for span in hit.spans:
            file_context.add_span_to_context(hit.file_path, span.span_id, tokens=25)

    code_contexts = ""
    # for f, v in file_context.get_contexts().items():
    #     print(f, [span.span_id for span in v.spans])

    # code_contexts += file_context.create_prompt(
    #     show_span_ids=False,
    #     show_line_numbers=False,
    #     exclude_comments=True,
    #     show_outcommented_code=False,
    # )

    return file_context.get_contexts().items()


def search_cluster(query: str, code_index: CodeIndex, workspace: Workspace):
    cluster_results = code_index.search(query, store_type=VectorStoreType.CLUSTER)
    file_context = workspace.create_file_context(files_with_spans=cluster_results.hits)

    for hit in cluster_results.hits:
        for span in hit.spans:
            file_context.add_span_to_context(hit.file_path, span.span_id, tokens=25)

    # for f, v in file_context.get_contexts().items():
    #     print(f, [span.span_id for span in v.spans])

    return file_context.get_contexts().items()


def search(query, code_index, workspace):
    repo_dir = os.path.join(REPOS_ROOT, repo_name)
    persist_dir = os.path.join(INDEX_ROOT, repo_name)
    cluster_json = {}

    for i, query in enumerate(queries):
        print("[Query] ===> ", query)

        code_results = search_code(query, code_index, workspace)
        cluster_results = search_cluster(query, code_index, workspace)

        span_set = []

        print("++++++ Code Results ++++++: ")
        for f, v in code_results:
            print("[File]: ", f)
            for span in [span.span_id for span in v.spans]:
                span_set.append(span)
                print(span)

        # print("||||||| Cluster Results ||||||||: ")
        # for f, v in cluster_results:
        #     print("[File]: ", f)
        #     for span in [span.span_id for span in v.spans]:
        #         span_set.append(span)
        #         print(span)

        # Uncomment and modify as needed
        # res = asyncio.run(answer(query, code_contexts))
        # search_ans = {
        #     "query": query,
        #     "response": res,
        #     "code_contexts": code_contexts,
        # }

        # with open(f"{i}", "w") as file:
        #     file.write(res)

        print(
            "---------------------------------------------------------------------------------"
        )


if __name__ == "__main__":
    search()
