import ell
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)
from pydantic import BaseModel


class EngagementAdvice(BaseModel):
    kinetic: str
    psychological: str


ell.init(store="./logdir", autocommit=True)


@ell.complex(model="gpt-4o-2024-08-06", response_format=EngagementAdvice)
# @retry(
#     wait=wait_random_exponential(min=1, max=15),
#     reraise=True,
#     stop=stop_after_attempt(3),
# )
def hello(name: str):
    """You are a helpful assistant."""
    return f"Return some questions about a milliatry engagement in {name} with structured outputs"


greeting = hello("Sam Altman")
print(greeting.parsed)
