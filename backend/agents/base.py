from abc import ABC, abstractmethod
from typing import Any

from backend.services.llm.base import LLMProvider
from backend.rag import CodeRetriever


class BaseAgent(ABC):
    """Base class for all agents."""

    name: str = "base"
    description: str = "Base agent"

    def __init__(self, llm: LLMProvider, retriever: CodeRetriever | None = None):
        self.llm = llm
        self.retriever = retriever

    @abstractmethod
    async def run(self, **kwargs) -> dict[str, Any]:
        """Run the agent with given inputs."""
        pass
