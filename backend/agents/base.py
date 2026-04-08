from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from backend.models.events import EventType, StreamEvent
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

    async def run_stream(self, **kwargs) -> AsyncIterator[StreamEvent]:
        """Stream agent execution events. Default wraps run()."""
        yield StreamEvent(event=EventType.AGENT_START, agent=self.name)
        try:
            result = await self.run(**kwargs)
            yield StreamEvent(event=EventType.RESULT, agent=self.name, data=result)
        except Exception as e:
            yield StreamEvent(
                event=EventType.ERROR, agent=self.name, data={"error": str(e)}
            )
        yield StreamEvent(event=EventType.DONE, agent=self.name)
