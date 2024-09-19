from typing import Optional

from codesearch.moatless.codeblocks.codeblocks import CodeBlock, CodeBlockType
from codesearch.moatless.codeblocks.parser.create import create_parser
from codesearch.moatless.codeblocks.parser.java import JavaParser
from codesearch.moatless.codeblocks.parser.parser import CodeParser
from codesearch.moatless.codeblocks.parser.python import PythonParser


def supports_codeblocks(path: str):
    return path.endswith(".py")


def get_parser_by_path(file_path: str) -> Optional[CodeParser]:
    if file_path.endswith(".py"):
        return PythonParser()
    elif file_path.endswith(".java"):
        return JavaParser()
    else:
        return None
