import numpy as np
from sklearn.cluster import AgglomerativeClustering

from backend.diff import ParsedDiff
from backend.rag.embeddings import EmbeddingService
from .base import ClusteringStrategy
from .models import CommitGroup, HunkReference


class SemanticStrategy(ClusteringStrategy):

    name = "semantic"
    description = "Group semantically related changes using embeddings"

    def __init__(
        self,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.5,
        max_clusters: int = 10,
    ):
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_clusters = max_clusters

    async def cluster(self, parsed_diff: ParsedDiff) -> list[CommitGroup]:
        all_hunks = parsed_diff.get_all_hunks()

        if len(all_hunks) <= 1:
            return self._single_group(all_hunks)

        hunk_texts = [
            f"File: {file.path}\n{hunk.section_header}\n{hunk.content}"
            for file, hunk in all_hunks
        ]

        embeddings = await self.embedding_service.embed_texts(hunk_texts)
        embeddings_array = np.array(embeddings)

        n_samples = len(all_hunks)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(embeddings_array)

        groups: dict[int, CommitGroup] = {}
        for idx, (file, hunk) in enumerate(all_hunks):
            label = int(labels[idx])

            if label not in groups:
                groups[label] = CommitGroup(
                    id=f"semantic-{label}",
                    hunks=[],
                    files=[],
                    reasoning=f"Semantically similar changes (cluster {label})",
                )

            groups[label].hunks.append(
                HunkReference(file_path=file.path, hunk_id=hunk.id)
            )
            if file.path not in groups[label].files:
                groups[label].files.append(file.path)

        return list(groups.values())

    def _single_group(self, all_hunks: list) -> list[CommitGroup]:
        if not all_hunks:
            return []

        return [
            CommitGroup(
                id="semantic-0",
                hunks=[
                    HunkReference(file_path=f.path, hunk_id=h.id) for f, h in all_hunks
                ],
                files=list(set(f.path for f, _ in all_hunks)),
                reasoning="Single change group",
            )
        ]
