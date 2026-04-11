"""T8: CS2 Crawler 网络层降级 + 重试测试（mock httpx）"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.crawlers.csgoskins_gg import CSGOSkinsGGCrawler
from app.crawlers.steam_market import SteamMarketCrawler


# =============== CSGOSKINS.GG 降级测试 ===============

class TestCSGOSkinsGGDegrade:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_api_key(self):
        """无 API key 时安全降级"""
        crawler = CSGOSkinsGGCrawler()
        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="")):
            result = await crawler.fetch_multi_platform("AK-47 | Redline")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_402_quota(self):
        """HTTP 402 配额耗尽时降级返回空"""
        crawler = CSGOSkinsGGCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 402

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="fake-key")), \
             patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_multi_platform("AK-47 | Redline")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_403_forbidden(self):
        crawler = CSGOSkinsGGCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 403

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="fake-key")), \
             patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_multi_platform("test")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_429_rate_limit(self):
        crawler = CSGOSkinsGGCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="fake-key")), \
             patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_multi_platform("test")
            assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_exception(self):
        """网络异常时降级，不抛异常"""
        crawler = CSGOSkinsGGCrawler()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="fake-key")), \
             patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_multi_platform("test")
            assert result == []

    @pytest.mark.asyncio
    async def test_parses_markets_on_success(self):
        crawler = CSGOSkinsGGCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "markets": [
                {"name": "Steam", "price": 3240.00, "currency": "CNY", "url": "https://steam.com/x"},
                {"name": "BUFF", "price": 3100.00, "currency": "CNY", "url": "https://buff.com/x"},
                {"name": "Invalid", "price": None, "currency": "CNY"},  # 应被过滤
            ],
        })

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.crawlers.csgoskins_gg._get_api_key", new=AsyncMock(return_value="fake-key")), \
             patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_multi_platform("AK-47 | Redline")
            assert len(result) == 2
            names = {r["platform"] for r in result}
            assert names == {"Steam", "BUFF"}


# =============== Steam Market 降级 + 重试测试 ===============

class TestSteamMarketCrawler:
    @pytest.mark.asyncio
    async def test_fetch_one_success(self):
        crawler = SteamMarketCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "success": True,
            "lowest_price": "¥ 3,240.00",
            "median_price": "¥ 3,200.50",
            "volume": "1,892",
        })

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_one(mock_client, "AK-47 | Redline (Field-Tested)")
        assert result is not None
        assert result["price"] == 3240.0
        assert result["median_price"] == 3200.5
        assert result["volume"] == 1892

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none_on_non_200(self):
        crawler = SteamMarketCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_one(mock_client, "AK-47")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none_on_api_success_false(self):
        crawler = SteamMarketCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"success": False})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_one(mock_client, "Nonexistent Item")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_one_retries_on_429(self):
        """429 时触发退避重试"""
        crawler = SteamMarketCrawler()

        call_count = {"n": 0}

        def get_side_effect(*args, **kwargs):
            call_count["n"] += 1
            resp = MagicMock(spec=httpx.Response)
            if call_count["n"] < 3:
                resp.status_code = 429
            else:
                resp.status_code = 200
                resp.json = MagicMock(return_value={
                    "success": True,
                    "lowest_price": "¥ 100.00",
                    "median_price": "¥ 99.00",
                    "volume": "50",
                })
            return resp

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=get_side_effect)

        # Patch asyncio.sleep 加速测试
        with patch("app.crawlers.steam_market.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await crawler.fetch_one(mock_client, "AK-47")

        assert call_count["n"] == 3
        assert result is not None
        assert result["price"] == 100.0

    @pytest.mark.asyncio
    async def test_fetch_one_gives_up_after_3_attempts(self):
        crawler = SteamMarketCrawler()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 429

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.crawlers.steam_market.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await crawler.fetch_one(mock_client, "AK-47")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_one_handles_timeout(self):
        crawler = SteamMarketCrawler()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.crawlers.steam_market.asyncio.sleep", new=AsyncMock(return_value=None)):
            result = await crawler.fetch_one(mock_client, "AK-47")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_prices_skips_items_with_none_price(self):
        """批量拉取时过滤掉价格为 None 的结果"""
        crawler = SteamMarketCrawler()

        # Mock fetch_one 返回部分 None
        call_count = {"n": 0}

        async def fake_fetch_one(client, name, currency=23):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"market_hash_name": name, "price": 100.0, "volume": 50}
            return None  # 第二个失败

        with patch.object(crawler, "fetch_one", side_effect=fake_fetch_one), \
             patch("app.crawlers.steam_market.asyncio.sleep", new=AsyncMock(return_value=None)):
            results = await crawler.fetch_prices(["item1", "item2"])

        assert len(results) == 1
        assert results[0]["market_hash_name"] == "item1"
