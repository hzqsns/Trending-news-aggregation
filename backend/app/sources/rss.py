import logging
from datetime import datetime
from time import mktime

import feedparser
import httpx

from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)

DEFAULT_RSS_FEEDS = [
    # --- 国际财经（一手）---
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "global",
    },
    {
        "name": "Reuters Markets",
        "url": "https://feeds.reuters.com/reuters/financialNews",
        "category": "global",
    },
    {
        "name": "CNBC Finance",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "category": "global",
    },
    {
        "name": "CNBC Economy",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
        "category": "global",
    },
    {
        "name": "WSJ Markets",
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "category": "global",
    },
    {
        "name": "WSJ Economy",
        "url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "category": "global",
    },
    {
        "name": "Financial Times",
        "url": "https://www.ft.com/rss/home",
        "category": "global",
    },
    {
        "name": "The Guardian Business",
        "url": "https://www.theguardian.com/business/rss",
        "category": "global",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "category": "global",
    },
    {
        "name": "AP Business",
        "url": "https://feeds.apnews.com/rss/apf-business",
        "category": "global",
    },
    {
        "name": "Axios Markets",
        "url": "https://api.axios.com/feed/",
        "category": "global",
    },
    # --- 加密 ---
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "category": "crypto",
    },
    {
        "name": "The Block",
        "url": "https://www.theblock.co/rss.xml",
        "category": "crypto",
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "category": "crypto",
    },
    # --- 科技 ---
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech",
    },
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech",
    },
    # --- 中文财经 ---
    {
        "name": "华尔街见闻",
        "url": "https://wallstreetcn.com/rss",
        "category": "global",
    },
    {
        "name": "新浪财经",
        "url": "https://finance.sina.com.cn/rss/economy.xml",
        "category": "a_stock",
    },
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "tech",
    },
    # --- AI 行业快讯（公司/IPO/融资/大模型发布）---
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/rss",
        "category": "ai_industry",
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/feed",
        "category": "ai_industry",
    },
    {
        "name": "36氪快讯",
        "url": "https://36kr.com/feed-article-newsflashes",
        "category": "ai_industry",
    },
    {
        "name": "虎嗅",
        "url": "https://www.huxiu.com/rss/0.xml",
        "category": "ai_industry",
    },
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "ai_industry",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "ai_industry",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "ai_industry",
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "ai_industry",
    },
]


class RSSSource(NewsSource):
    name = "RSS"
    enabled_key = "source_rss_enabled"

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or DEFAULT_RSS_FEEDS

    async def fetch(self) -> list[NewsItem]:
        items = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for feed_cfg in self.feeds:
                try:
                    resp = await client.get(
                        feed_cfg["url"],
                        headers={"User-Agent": "Mozilla/5.0 NewsAgent/2.0"},
                    )
                    if resp.status_code != 200:
                        logger.warning(f"RSS {feed_cfg['name']} returned {resp.status_code}")
                        continue

                    parsed = feedparser.parse(resp.text)
                    for entry in parsed.entries[:20]:
                        pub_date = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                            pub_date = datetime.fromtimestamp(mktime(entry.updated_parsed))

                        summary = ""
                        if hasattr(entry, "summary"):
                            summary = entry.summary[:500]

                        image_url = None
                        if hasattr(entry, "media_content") and entry.media_content:
                            image_url = entry.media_content[0].get("url")
                        elif hasattr(entry, "enclosures") and entry.enclosures:
                            image_url = entry.enclosures[0].get("href")

                        items.append(NewsItem(
                            title=entry.get("title", "").strip(),
                            url=entry.get("link", ""),
                            source=feed_cfg["name"],
                            category=feed_cfg.get("category", "general"),
                            summary=summary,
                            image_url=image_url,
                            published_at=pub_date,
                        ))
                except Exception as e:
                    logger.error(f"Error fetching RSS {feed_cfg['name']}: {e}")
        return items
