from starlette.config import Config
from urllib.parse import urljoin
import os

from enum import Enum

config = Config(".env")

ENV = config("ENV", default="dev")
CODESEARCH_DIR = (
    "/home/ubuntu"
    if ENV == "release"
    else r"C:\Users\jpeng\Documents\projects\codesearch-backend\data"
)
PORT = int(config("PORT", default=3000))

# JWT settings
COWBOY_JWT_SECRET = config("DISPATCH_JWT_SECRET", default="")
COWBOY_JWT_ALG = config("DISPATCH_JWT_ALG", default="HS256")
COWBOY_JWT_EXP = config("DISPATCH_JWT_EXP", cast=int, default=308790000)  # Seconds

COWBOY_OPENAI_API_KEY = config("OPENAI_API_KEY")

DB_PASS = config("DB_PASS")
SQLALCHEMY_DATABASE_URI = f"postgresql://postgres:{DB_PASS}@127.0.0.1:5432/codesearch"
SQLALCHEMY_ENGINE_POOL_SIZE = 50

ALEMBIC_INI_PATH = "."
ALEMBIC_CORE_REVISION_PATH = "alembic"

# LLM settings and test gen settings
AUGMENT_ROUNDS = 4 if ENV == "release" else 1
LLM_RETRIES = 3
AUTO_GEN_SIZE = 7
LOG_DIR = "log"

REPOS_ROOT = os.path.join(CODESEARCH_DIR, "repo")
INDEX_ROOT = os.path.join(CODESEARCH_DIR, "index")
GRAPH_ROOT = os.path.join(CODESEARCH_DIR, "graphs")
SUMMARIES_ROOT = os.path.join(CODESEARCH_DIR, "summaries")

AWS_REGION = "us-east-2"
# MAX_REPO_SIZE =

# Anonymous user
ANON_LOGIN = True


class Language(str, Enum):
    """
    Currently supported languages
    """

    python = "python"
