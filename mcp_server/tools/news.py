"""
EcoSight MCP Tool — News
Fetch top headlines and search news, with TTS-friendly summaries.

Uses NewsAPI (newsapi.org).
"""

from __future__ import annotations

import httpx
from typing import Any

from mcp_server.config import NEWS_API_KEY, NEWS_BASE_URL


def _spoken_article(article: dict) -> str:
    """Turn one article into a short spoken summary."""
    title = article.get("title", "Untitled")
    source = article.get("source", {}).get("name", "unknown source")
    description = article.get("description") or ""
    if len(description) > 200:
        description = description[:200].rsplit(" ", 1)[0] + "..."
    return f"From {source}: {title}. {description}"


async def get_top_headlines(
    country: str = "us",
    category: str | None = None,
    count: int = 5,
) -> dict[str, Any]:
    """
    Fetch today's top news headlines.

    Args:
        country:  ISO 3166-1 country code (e.g. "us", "in", "gb").
        category: Optional — business, entertainment, general, health,
                  science, sports, technology.
        count:    Number of articles (max 10).

    Returns:
        spoken_summary – ready for TTS
        articles       – list of article dicts
    """
    count = min(count, 10)
    params: dict[str, Any] = {
        "apiKey": NEWS_API_KEY,
        "country": country,
        "pageSize": count,
    }
    if category:
        params["category"] = category

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{NEWS_BASE_URL}/top-headlines", params=params)
        resp.raise_for_status()
        data = resp.json()

    articles = data.get("articles", [])
    summaries: list[dict] = []
    spoken_parts: list[str] = []

    for i, art in enumerate(articles[:count], 1):
        summary = {
            "number": i,
            "title": art.get("title", ""),
            "source": art.get("source", {}).get("name", ""),
            "description": art.get("description", ""),
            "url": art.get("url", ""),
            "published_at": art.get("publishedAt", ""),
        }
        summaries.append(summary)
        spoken_parts.append(f"Number {i}: {_spoken_article(art)}")

    cat_label = f" in {category}" if category else ""
    spoken = f"Here are the top {len(summaries)} headlines{cat_label}. " + " ".join(spoken_parts)

    return {
        "spoken_summary": spoken,
        "total_results": data.get("totalResults", 0),
        "articles": summaries,
    }


async def search_news(
    query: str,
    count: int = 5,
    sort_by: str = "relevancy",
) -> dict[str, Any]:
    """
    Search news articles by keyword.

    Args:
        query:   Search terms (e.g. "accessible sidewalks", "weather emergency").
        count:   Number of results (max 10).
        sort_by: "relevancy", "popularity", or "publishedAt".

    Returns:
        spoken_summary – TTS-ready overview
        articles       – list of article dicts
    """
    count = min(count, 10)
    params: dict[str, Any] = {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "pageSize": count,
        "sortBy": sort_by,
        "language": "en",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{NEWS_BASE_URL}/everything", params=params)
        resp.raise_for_status()
        data = resp.json()

    articles = data.get("articles", [])
    summaries: list[dict] = []
    spoken_parts: list[str] = []

    for i, art in enumerate(articles[:count], 1):
        summary = {
            "number": i,
            "title": art.get("title", ""),
            "source": art.get("source", {}).get("name", ""),
            "description": art.get("description", ""),
            "url": art.get("url", ""),
            "published_at": art.get("publishedAt", ""),
        }
        summaries.append(summary)
        spoken_parts.append(f"Number {i}: {_spoken_article(art)}")

    spoken = f"Found {data.get('totalResults', 0)} results for '{query}'. " + " ".join(spoken_parts)

    return {
        "spoken_summary": spoken,
        "total_results": data.get("totalResults", 0),
        "articles": summaries,
    }
