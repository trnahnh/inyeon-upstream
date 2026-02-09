import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.diff import ParsedDiff, ParsedFile, ParsedHunk, FileChangeType
from backend.clustering import (
    DirectoryStrategy,
    ConventionalStrategy,
    HybridStrategy,
    CommitGroup,
)


@pytest.fixture
def sample_parsed_diff():
    return ParsedDiff(
        files=[
            ParsedFile(
                path="backend/agents/commit.py",
                change_type=FileChangeType.MODIFIED,
                hunks=[
                    ParsedHunk(
                        id="backend/agents/commit.py:0",
                        source_start=1,
                        source_length=5,
                        target_start=1,
                        target_length=7,
                        section_header="def generate_commit",
                        lines=[],
                        added_count=3,
                        removed_count=1,
                    )
                ],
            ),
            ParsedFile(
                path="backend/agents/review.py",
                change_type=FileChangeType.MODIFIED,
                hunks=[
                    ParsedHunk(
                        id="backend/agents/review.py:0",
                        source_start=10,
                        source_length=3,
                        target_start=10,
                        target_length=5,
                        section_header="def review_code",
                        lines=[],
                        added_count=2,
                        removed_count=0,
                    )
                ],
            ),
            ParsedFile(
                path="tests/test_agents.py",
                change_type=FileChangeType.ADDED,
                hunks=[
                    ParsedHunk(
                        id="tests/test_agents.py:0",
                        source_start=0,
                        source_length=0,
                        target_start=1,
                        target_length=10,
                        section_header="",
                        lines=[],
                        added_count=10,
                        removed_count=0,
                    )
                ],
            ),
            ParsedFile(
                path="README.md",
                change_type=FileChangeType.MODIFIED,
                hunks=[
                    ParsedHunk(
                        id="README.md:0",
                        source_start=1,
                        source_length=2,
                        target_start=1,
                        target_length=3,
                        section_header="",
                        lines=[],
                        added_count=1,
                        removed_count=0,
                    )
                ],
            ),
        ],
        total_added=16,
        total_removed=1,
    )


@pytest.fixture
def empty_parsed_diff():
    return ParsedDiff(files=[], total_added=0, total_removed=0)


@pytest.fixture
def single_file_diff():
    return ParsedDiff(
        files=[
            ParsedFile(
                path="main.py",
                change_type=FileChangeType.MODIFIED,
                hunks=[
                    ParsedHunk(
                        id="main.py:0",
                        source_start=1,
                        source_length=1,
                        target_start=1,
                        target_length=2,
                        section_header="",
                        lines=[],
                        added_count=1,
                        removed_count=0,
                    )
                ],
            )
        ],
        total_added=1,
        total_removed=0,
    )


class TestDirectoryStrategy:

    @pytest.mark.asyncio
    async def test_cluster_by_directory(self, sample_parsed_diff):
        strategy = DirectoryStrategy(max_depth=2)
        groups = await strategy.cluster(sample_parsed_diff)

        assert len(groups) > 0
        assert all(isinstance(g, CommitGroup) for g in groups)

    @pytest.mark.asyncio
    async def test_cluster_empty_diff(self, empty_parsed_diff):
        strategy = DirectoryStrategy()
        groups = await strategy.cluster(empty_parsed_diff)

        assert len(groups) == 0

    @pytest.mark.asyncio
    async def test_cluster_groups_same_directory(self, sample_parsed_diff):
        strategy = DirectoryStrategy(max_depth=2)
        groups = await strategy.cluster(sample_parsed_diff)

        backend_group = next(
            (g for g in groups if "backend/agents" in g.files[0]), None
        )
        assert backend_group is not None
        assert len(backend_group.files) == 2
        assert "backend/agents/commit.py" in backend_group.files
        assert "backend/agents/review.py" in backend_group.files

    @pytest.mark.asyncio
    async def test_cluster_root_files(self, sample_parsed_diff):
        strategy = DirectoryStrategy(max_depth=2)
        groups = await strategy.cluster(sample_parsed_diff)

        root_group = next((g for g in groups if "README.md" in g.files), None)
        assert root_group is not None

    @pytest.mark.asyncio
    async def test_cluster_creates_unique_ids(self, sample_parsed_diff):
        strategy = DirectoryStrategy()
        groups = await strategy.cluster(sample_parsed_diff)

        ids = [g.id for g in groups]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_cluster_max_depth(self, sample_parsed_diff):
        strategy_depth1 = DirectoryStrategy(max_depth=1)
        strategy_depth2 = DirectoryStrategy(max_depth=2)

        groups1 = await strategy_depth1.cluster(sample_parsed_diff)
        groups2 = await strategy_depth2.cluster(sample_parsed_diff)

        assert len(groups1) <= len(groups2)


class TestConventionalStrategy:

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value={"text": "feat"})
        return llm

    @pytest.mark.asyncio
    async def test_cluster_by_type(self, sample_parsed_diff, mock_llm):
        mock_llm.generate = AsyncMock(
            side_effect=[
                {"text": "feat"},
                {"text": "feat"},
                {"text": "test"},
                {"text": "docs"},
            ]
        )

        strategy = ConventionalStrategy(mock_llm)
        groups = await strategy.cluster(sample_parsed_diff)

        assert len(groups) == 3
        types = [g.suggested_type for g in groups]
        assert "feat" in types
        assert "test" in types
        assert "docs" in types

    @pytest.mark.asyncio
    async def test_cluster_invalid_type_defaults_to_chore(
        self, single_file_diff, mock_llm
    ):
        mock_llm.generate = AsyncMock(return_value={"text": "invalid_type"})

        strategy = ConventionalStrategy(mock_llm)
        groups = await strategy.cluster(single_file_diff)

        assert len(groups) == 1
        assert groups[0].suggested_type == "chore"

    @pytest.mark.asyncio
    async def test_cluster_empty_diff(self, empty_parsed_diff, mock_llm):
        strategy = ConventionalStrategy(mock_llm)
        groups = await strategy.cluster(empty_parsed_diff)

        assert len(groups) == 0
        mock_llm.generate.assert_not_called()


class TestHybridStrategy:

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value={"text": "feat"})
        return llm

    @pytest.mark.asyncio
    async def test_hybrid_combines_strategies(self, sample_parsed_diff, mock_llm):
        strategy = HybridStrategy(llm=mock_llm, embedding_service=None)
        groups = await strategy.cluster(sample_parsed_diff)

        assert len(groups) > 0
        assert all(isinstance(g, CommitGroup) for g in groups)

    @pytest.mark.asyncio
    async def test_hybrid_empty_diff(self, empty_parsed_diff, mock_llm):
        strategy = HybridStrategy(llm=mock_llm, embedding_service=None)
        groups = await strategy.cluster(empty_parsed_diff)

        assert len(groups) == 0

    @pytest.mark.asyncio
    async def test_hybrid_assigns_types(self, sample_parsed_diff, mock_llm):
        strategy = HybridStrategy(llm=mock_llm, embedding_service=None)
        groups = await strategy.cluster(sample_parsed_diff)

        for group in groups:
            assert group.suggested_type is not None


class TestCommitGroup:

    def test_commit_group_file_count(self):
        group = CommitGroup(
            id="test-1",
            files=["a.py", "b.py", "a.py"],
            hunks=[],
        )
        assert group.file_count == 2

    def test_commit_group_hunk_count(self):
        from backend.clustering.models import HunkReference

        group = CommitGroup(
            id="test-1",
            files=[],
            hunks=[
                HunkReference(file_path="a.py", hunk_id="a.py:0"),
                HunkReference(file_path="a.py", hunk_id="a.py:1"),
            ],
        )
        assert group.hunk_count == 2
