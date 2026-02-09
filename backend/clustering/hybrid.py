from backend.diff import ParsedDiff, ParsedFile, ParsedHunk
from backend.services.llm.base import LLMProvider
from backend.rag.embeddings import EmbeddingService
from .base import ClusteringStrategy
from .directory import DirectoryStrategy
from .semantic import SemanticStrategy
from .conventional import ConventionalStrategy
from .models import CommitGroup


class HybridStrategy(ClusteringStrategy):

    name = "hybrid"
    description = (
        "Intelligent combination of directory, semantic, and type-based clustering"
    )

    def __init__(
        self,
        llm: LLMProvider,
        embedding_service: EmbeddingService | None = None,
    ):
        self.llm = llm
        self.embedding_service = embedding_service
        self.directory = DirectoryStrategy()
        self.conventional = ConventionalStrategy(llm)

    async def cluster(self, parsed_diff: ParsedDiff) -> list[CommitGroup]:
        dir_groups = await self.directory.cluster(parsed_diff)

        refined_groups = []
        for group in dir_groups:
            if len(group.hunks) > 3 and self.embedding_service:
                sub_diff = self._extract_subdiff(parsed_diff, group)
                semantic = SemanticStrategy(self.embedding_service)
                semantic_subgroups = await semantic.cluster(sub_diff)
                refined_groups.extend(semantic_subgroups)
            else:
                refined_groups.append(group)

        for group in refined_groups:
            sub_diff = self._extract_subdiff(parsed_diff, group)
            if sub_diff.files:
                type_groups = await self.conventional.cluster(sub_diff)
                if type_groups:
                    group.suggested_type = type_groups[0].suggested_type

        return refined_groups

    def _extract_subdiff(self, full_diff: ParsedDiff, group: CommitGroup) -> ParsedDiff:
        files = [f for f in full_diff.files if f.path in group.files]
        return ParsedDiff(
            files=files,
            total_added=sum(h.added_count for f in files for h in f.hunks),
            total_removed=sum(h.removed_count for f in files for h in f.hunks),
        )
