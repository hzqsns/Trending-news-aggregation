"""T9: CS2 Patchnotes Crawler — BBCode/HTML 清理 + 返回结构"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.crawlers.cs2_patchnotes import CS2PatchNotesCrawler


class TestCS2PatchNotesCrawler:
    @pytest.mark.asyncio
    async def test_returns_empty_on_non_200(self):
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(10)
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        crawler = CS2PatchNotesCrawler()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(10)
            assert result == []

    @pytest.mark.asyncio
    async def test_strips_bbcode_tags(self):
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "appnews": {
                "newsitems": [
                    {
                        "title": "Counter-Strike 2 Update",
                        "url": "https://steamcommunity.com/app/730/news/123",
                        "contents": "[h1]Patch notes[/h1][list][*]Fixed a bug[*]Added new map[/list]",
                        "date": 1728000000,
                        "author": "Valve",
                    }
                ]
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(1)

        assert len(result) == 1
        item = result[0]
        # BBCode 标签应被移除
        assert "[h1]" not in item["summary"]
        assert "[list]" not in item["summary"]
        assert "[/list]" not in item["summary"]
        assert "[*]" not in item["summary"]
        # 但是内容文本应保留
        assert "Patch notes" in item["summary"]
        assert "Fixed a bug" in item["summary"]

    @pytest.mark.asyncio
    async def test_strips_html_tags(self):
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "appnews": {
                "newsitems": [
                    {
                        "title": "Update",
                        "url": "https://x.com/1",
                        "contents": "<p>New update!</p><br/><strong>Fixes</strong>: crash",
                        "date": 1728000000,
                    }
                ]
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(1)

        assert "<p>" not in result[0]["summary"]
        assert "<br/>" not in result[0]["summary"]
        assert "<strong>" not in result[0]["summary"]
        assert "New update!" in result[0]["summary"]
        assert "Fixes" in result[0]["summary"]

    @pytest.mark.asyncio
    async def test_parses_timestamp(self):
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "appnews": {
                "newsitems": [
                    {
                        "title": "T",
                        "url": "u",
                        "contents": "c",
                        "date": 1728000000,  # 2024-10-04 UTC
                    }
                ]
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(1)

        assert result[0]["published_at"] is not None
        assert "2024" in result[0]["published_at"]

    @pytest.mark.asyncio
    async def test_summary_truncated_to_500(self):
        crawler = CS2PatchNotesCrawler()
        long_content = "a" * 1000
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "appnews": {
                "newsitems": [
                    {"title": "T", "url": "u", "contents": long_content, "date": 0}
                ]
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(1)

        assert len(result[0]["summary"]) <= 500

    @pytest.mark.asyncio
    async def test_returns_empty_on_empty_newsitems(self):
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"appnews": {"newsitems": []}})

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(10)
            assert result == []

    @pytest.mark.asyncio
    async def test_handles_missing_fields_gracefully(self):
        """API 返回缺少某些字段时不应抛异常"""
        crawler = CS2PatchNotesCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "appnews": {
                "newsitems": [
                    {"title": "Partial"}  # 只有 title
                ]
            }
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_recent(1)

        assert len(result) == 1
        assert result[0]["title"] == "Partial"
        assert result[0]["url"] == ""
        assert result[0]["published_at"] is None
