
"""
tools/web_presence/search_presence_tool.py

Search for public web evidence about a company.
Standalone function first; CrewAI integration comes later.
"""

from backend.config import settings


def search_company_presence(
    company_name: str,
    website: str | None = None,
) -> dict:
    """
    Search for public web evidence about a company.

    Status values:
      found          One or more search results were returned.
      not_found      Search succeeded but returned no results.
      unavailable    Search could not run due to missing configuration.
      error          Search provider failed.

    IMPORTANT:
    A 'found' status does not confirm company identity.
    Each result must be assessed for relevance and source reliability.
    """
    company_name = (company_name or "").strip()

    if not company_name:
        return {
            "status": "invalid_input",
            "company": None,
            "results": [],
            "error": "Company name is required",
        }

    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return {
            "status": "unavailable",
            "company": company_name,
            "results": [],
            "error": "TAVILY_API_KEY is not configured",
        }

    query = f'"{company_name}" official website company'
    if website and website.strip():
        query += f' {website.strip()}'

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=5,
            search_depth="basic",
        )

        raw_results = response.get("results", []) or []
        results = []

        for item in raw_results:
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
                "score": item.get("score"),
            })

        return {
            "status": "found" if results else "not_found",
            "company": company_name,
            "query": query,
            "results": results,
            "error": None,
        }

    except Exception as exc:
        return {
            "status": "error",
            "company": company_name,
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
