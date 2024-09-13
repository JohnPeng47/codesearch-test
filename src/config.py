from starlette.config import Config
from urllib.parse import urljoin

from enum import Enum

config = Config(".env")

ENV = config("ENV", default="dev")
PORT = int(config("PORT"))
API_ENDPOINT = urljoin(config("HOST"), str(PORT))

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

# TODO: auto-create these
REPOS_ROOT = "/home/ubuntu/repos"
INDEX_ROOT = "/home/ubuntu/index"
GRAPH_ROOT = "/home/ubuntu/graphs"
SUMMARIES_ROOT = "/home/ubuntu/summaries"

AWS_REGION = "us-east-2"

SSH_KEY_PATH = config("SSH_KEY_PATH")
# MAX_REPO_SIZE = 

# Anonymous user
ANON_LOGIN = True

class Language(str, Enum):
    """
    Currently supported languages
    """

    python = "python"
