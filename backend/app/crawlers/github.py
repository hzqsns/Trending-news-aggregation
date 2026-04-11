import logging
from datetime import datetime, timezone

import httpx

from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://api.github.com/search/repositories"


class GitHubTrendingCrawler(CrawlerPlugin):
    key = "github"
    name = "GitHub Trending"
    category = "tech"
    enabled_key = "source_github_enabled"

    async def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    GITHUB_TRENDING_URL,
                    params={
                        "q": f"created:>{today}",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 30,
                    },
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "NewsAgent/2.0",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(f"GitHub API returned {resp.status_code}")
                    return items

                data = resp.json()
                for repo in data.get("items", [])[:30]:
                    created = None
                    if repo.get("created_at"):
                        try:
                            created = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass

                    lang = repo.get("language") or "Unknown"
                    stars = repo.get("stargazers_count", 0)
                    items.append(NewsItem(
                        title=f"[{lang}] {repo.get('full_name', '')} ({stars} stars)",
                        url=repo.get("html_url", ""),
                        source="GitHub",
                        category="tech",
                        summary=repo.get("description", "")[:500] if repo.get("description") else None,
                        published_at=created,
                    ))
        except Exception as e:
            logger.error(f"Error fetching GitHub trending: {e}")
        return items
