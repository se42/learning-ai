"""
Search Router — Knowledge Base Search

Rails posts a query, gets back relevant document snippets.
This is the pattern for "give me intelligence about my own data."

The search service is deliberately simple (keyword matching) to keep
this demo dependency-free. In production, swap in a vector store —
the API contract doesn't change.
"""

from fastapi import APIRouter, HTTPException

from app.models import SearchRequest, SearchResponse, SearchResult
from app.services.search_service import search_documents

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search the document corpus for relevant articles.

    Takes a natural language query, runs it against the local document
    corpus using keyword matching, and returns ranked results.

    In production, this endpoint would:
      1. Run the keyword search (or vector search)
      2. Optionally rerank results using an LLM
      3. Return the top results

    The Rails app doesn't need to know which approach is used — it just
    sends a query and gets back results.
    """
    try:
        raw_results = search_documents(
            query=request.query,
            max_results=request.max_results,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {e}",
        )

    # Convert raw dicts to typed SearchResult objects
    results = [
        SearchResult(
            title=r["title"],
            content=r["content"],
            score=r["score"],
            article_id=r["article_id"],
        )
        for r in raw_results
    ]

    # model_used is "keyword-search" because this demo doesn't use an LLM
    # for search. When you upgrade to embedding-based search, this would
    # change to something like "openai/text-embedding-3-small".
    return SearchResponse(
        results=results,
        query=request.query,
        model_used="keyword-search",
    )

    # -----------------------------------------------------------------------
    # Future: LLM-powered reranking
    #
    # Once you have basic search working, the next upgrade is to use an LLM
    # to rerank results for better relevance. The pattern:
    #
    #   from app.services.llm_factory import get_model
    #
    #   model = get_model("search")
    #   rerank_prompt = f"""
    #   Query: {request.query}
    #
    #   Rank these search results by relevance (most relevant first):
    #   {json.dumps(raw_results, indent=2)}
    #
    #   Return the article_ids in order of relevance as a JSON array.
    #   """
    #   response = await model.ainvoke([HumanMessage(content=rerank_prompt)])
    #   reranked_ids = json.loads(response.content)
    #
    # This gives you semantic understanding of relevance without needing
    # a vector store. It's a good intermediate step.
    # -----------------------------------------------------------------------
