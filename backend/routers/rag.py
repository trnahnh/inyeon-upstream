from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.rag import CodeRetriever, RAGError


router = APIRouter(tags=["rag"])

retrievers: dict[str, CodeRetriever] = {}


def get_retriever(repo_id: str) -> CodeRetriever:
    """Get or create retriever for a specific repo."""
    if repo_id not in retrievers:
        retrievers[repo_id] = CodeRetriever()
    return retrievers[repo_id]


class IndexRequest(BaseModel):
    repo_id: str
    files: dict[str, str]


class IndexResponse(BaseModel):
    indexed: int
    total: int


class SearchRequest(BaseModel):
    repo_id: str
    query: str
    n_results: int = 5


class SearchResult(BaseModel):
    path: str
    content: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class RepoRequest(BaseModel):
    repo_id: str


@router.post("/index", response_model=IndexResponse)
async def index_files(request: IndexRequest) -> IndexResponse:
    """Index files for a specific repo."""
    try:
        ret = get_retriever(request.repo_id)
        ids = await ret.index_files(request.files)
        return IndexResponse(indexed=len(ids), total=ret.count())
    except RAGError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {e}",
        )


@router.post("/search", response_model=SearchResponse)
async def search_code(request: SearchRequest) -> SearchResponse:
    """Search indexed code for a specific repo."""
    try:
        ret = get_retriever(request.repo_id)
        results = await ret.search(request.query, request.n_results)
        return SearchResponse(results=[SearchResult(**r) for r in results])
    except RAGError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e}",
        )


@router.post("/stats")
async def rag_stats(request: RepoRequest) -> dict:
    """Get RAG index statistics for a repo."""
    ret = get_retriever(request.repo_id)
    return {"repo_id": request.repo_id, "indexed_files": ret.count()}


@router.post("/clear")
async def clear_index(request: RepoRequest) -> dict:
    """Clear the RAG index for a repo."""
    ret = get_retriever(request.repo_id)
    ret.clear()
    return {"status": "cleared", "repo_id": request.repo_id}
