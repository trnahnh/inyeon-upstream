from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of streaming events emitted during agent execution."""

    AGENT_START = "agent_start"
    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    REASONING = "reasoning"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    DONE = "done"


class StreamEvent(BaseModel):
    """A single streaming event from an agent execution."""

    event: EventType
    agent: str = ""
    node: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
