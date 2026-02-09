from abc import ABC, abstractmethod

from backend.diff import ParsedDiff
from .models import CommitGroup


class ClusteringStrategy(ABC):

    name: str = "base"
    description: str = "Base clustering strategy"

    @abstractmethod
    async def cluster(self, parsed_diff: ParsedDiff) -> list[CommitGroup]:
        pass
