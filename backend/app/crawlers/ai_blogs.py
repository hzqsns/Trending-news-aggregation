"""AI 厂商官方博客 + 知名 AI 评论博主 RSS 抓取。"""

from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem
from app.sources.rss import RSSSource

AI_BLOG_FEEDS = [
    # 头部 AI 公司官方博客
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml", "category": "ai"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "category": "ai"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "category": "ai"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "category": "ai"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": "ai"},
    # 知名 AI 评论
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": "ai"},
    {"name": "Sebastian Raschka", "url": "https://magazine.sebastianraschka.com/feed", "category": "ai"},
    # AI 工程实践
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/", "category": "ai"},
]


class AIBlogsCrawler(CrawlerPlugin):
    key = "ai_blogs"
    name = "AI Blogs"
    category = "ai"
    enabled_key = None  # 始终启用，不依赖 system_settings 开关

    def __init__(self):
        self._source = RSSSource(feeds=AI_BLOG_FEEDS)

    async def fetch(self) -> list[NewsItem]:
        items = await self._source.fetch()
        # 强制 category=ai_industry 让评分 prompt 知道这是 AI 内容
        for it in items:
            it.category = "ai_industry"
        return items
