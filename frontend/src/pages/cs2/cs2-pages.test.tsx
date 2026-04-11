import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ToastProvider } from '@/components/ui'

// Mock cs2 API module before importing pages
vi.mock('@/api/cs2', () => ({
  cs2Api: {
    marketOverview: vi.fn(),
    hotItems: vi.fn(),
    rankings: vi.fn(),
    categories: vi.fn(),
    categoryTrend: vi.fn(),
    categoryTopItems: vi.fn(),
    itemDetail: vi.fn(),
    itemKline: vi.fn(),
    predictions: vi.fn(),
    regeneratePrediction: vi.fn(),
    watchlist: vi.fn(),
    addWatch: vi.fn(),
    updateWatch: vi.fn(),
    deleteWatch: vi.fn(),
    watchlistAlerts: vi.fn(),
  },
}))

import { cs2Api } from '@/api/cs2'
import Cs2Dashboard from './Dashboard'
import Cs2Rankings from './Rankings'
import Cs2Categories from './Categories'
import Cs2Predictions from './Predictions'
import Cs2Watchlist from './Watchlist'
import Cs2ItemDetail from './ItemDetail'

const mocked = {
  marketOverview: vi.mocked(cs2Api.marketOverview),
  hotItems: vi.mocked(cs2Api.hotItems),
  rankings: vi.mocked(cs2Api.rankings),
  categories: vi.mocked(cs2Api.categories),
  itemDetail: vi.mocked(cs2Api.itemDetail),
  itemKline: vi.mocked(cs2Api.itemKline),
  predictions: vi.mocked(cs2Api.predictions),
  watchlist: vi.mocked(cs2Api.watchlist),
}

describe('Cs2Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders market stats after data loads', async () => {
    mocked.marketOverview.mockResolvedValue({
      data: {
        period: '24h',
        total_items: 74,
        total_market_cap: 123456.78,
        total_volume: 42,
        gainers: 10,
        losers: 5,
        sentiment_index: 66,
      },
    } as never)
    mocked.hotItems.mockResolvedValue({
      data: {
        items: [
          { id: 1, display_name: 'AK-47 红线', category: 'rifle', rarity: 'classified', image_url: null, current_price: 100, volume_24h: 50 },
        ],
      },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Dashboard />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('CS2 市场总览')).toBeInTheDocument()
    })

    expect(screen.getByText('74')).toBeInTheDocument()  // total_items
    expect(screen.getByText('热门饰品 Top 10')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('AK-47 红线')).toBeInTheDocument()
    })
  })

  it('shows empty state when no hot items', async () => {
    mocked.marketOverview.mockResolvedValue({
      data: { period: '24h', total_items: 0, total_market_cap: 0, total_volume: 0, gainers: 0, losers: 0, sentiment_index: 50 },
    } as never)
    mocked.hotItems.mockResolvedValue({ data: { items: [] } } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Dashboard />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('暂无数据，等待首次采集')).toBeInTheDocument()
    })
  })
})

describe('Cs2Rankings', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders ranking table with items', async () => {
    mocked.rankings.mockResolvedValue({
      data: {
        items: [
          { id: 1, name: 'AK-47 红线', market_hash_name: 'ak', image_url: null, category: 'rifle', rarity: 'classified', current_price: 100, change_pct: 12.5, change_value: 11, volume: 50 },
          { id: 2, name: 'AWP 龙狙', market_hash_name: 'awp', image_url: null, category: 'rifle', rarity: 'covert', current_price: 10000, change_pct: 5.3, change_value: 500, volume: 8 },
        ],
        total: 2,
        page: 1,
        page_size: 20,
        pages: 1,
      },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Rankings />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('AK-47 红线')).toBeInTheDocument()
      expect(screen.getByText('AWP 龙狙')).toBeInTheDocument()
    })
    expect(screen.getByText('+12.50%')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mocked.rankings.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Rankings />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('暂无排行数据')).toBeInTheDocument()
    })
  })
})

describe('Cs2Categories', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders category grid', async () => {
    mocked.categories.mockResolvedValue({
      data: {
        categories: [
          { id: 'knife', name: 'knife', item_count: 12 },
          { id: 'rifle', name: 'rifle', item_count: 30 },
        ],
      },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Categories />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('刀具')).toBeInTheDocument()
      expect(screen.getByText('步枪')).toBeInTheDocument()
    })
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
  })

  it('shows empty state when no categories', async () => {
    mocked.categories.mockResolvedValue({ data: { categories: [] } } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Categories />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('暂无品类数据')).toBeInTheDocument()
    })
  })
})

describe('Cs2Predictions', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders prediction cards', async () => {
    mocked.predictions.mockResolvedValue({
      data: {
        period: '7d',
        items: [
          {
            id: 1,
            item_id: 1,
            period: '7d',
            direction: 'bullish',
            up_prob: 0.7,
            flat_prob: 0.2,
            down_prob: 0.1,
            confidence: 0.85,
            predicted_price: 120,
            reasoning: '成交量放大，趋势向上',
            factors: ['成交量', '社区热度'],
            generated_at: '2026-04-10T00:00:00',
            item_name: 'AK-47 红线',
            item_category: 'rifle',
          },
        ],
        total: 1,
        page: 1,
        pages: 1,
      },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Predictions />
      </ToastProvider></MemoryRouter>,
    )

    // 用 reasoning 文本（唯一）代替 "AK-47 红线" 验证卡片渲染
    // "看多" 在过滤按钮和 Badge 中都出现，用 getAllByText
    await waitFor(() => {
      expect(screen.getByText('成交量放大，趋势向上')).toBeInTheDocument()
    })
    expect(screen.getAllByText('看多').length).toBeGreaterThan(0)
  })

  it('shows empty state', async () => {
    mocked.predictions.mockResolvedValue({
      data: { period: '7d', items: [], total: 0, page: 1, pages: 0 },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Predictions />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/暂无预测数据/)).toBeInTheDocument()
    })
  })
})

describe('Cs2Watchlist', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders empty watchlist', async () => {
    mocked.watchlist.mockResolvedValue({ data: { items: [] } } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Watchlist />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/暂无自选饰品/)).toBeInTheDocument()
    })
  })

  it('renders watchlist items', async () => {
    mocked.watchlist.mockResolvedValue({
      data: {
        items: [
          {
            id: 1, item_id: 1, item_name: 'AK-47 红线', image_url: null,
            target_price: 150, alert_direction: 'above',
            current_price: 100, triggered: false, created_at: '2026-04-10',
          },
        ],
      },
    } as never)

    render(
      <MemoryRouter><ToastProvider>
        <Cs2Watchlist />
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('AK-47 红线')).toBeInTheDocument()
    })
    expect(screen.getByText('我的自选 (1)')).toBeInTheDocument()
  })
})

describe('Cs2ItemDetail', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders item detail with prediction', async () => {
    mocked.itemDetail.mockResolvedValue({
      data: {
        id: 1,
        display_name: 'AK-47 红线',
        category: 'rifle',
        subcategory: 'ak47',
        rarity: 'classified',
        image_url: null,
        current_price: 100,
        volume_24h: 50,
        prediction: {
          id: 1,
          item_id: 1,
          period: '7d',
          direction: 'bullish',
          up_prob: 0.7,
          flat_prob: 0.2,
          down_prob: 0.1,
          confidence: 0.85,
          predicted_price: 120,
          reasoning: '向上',
          factors: [],
          generated_at: '2026-04-10',
          item_name: 'AK-47 红线',
        },
      },
    } as never)
    mocked.itemKline.mockResolvedValue({
      data: {
        period: '7d',
        points: [
          { time: '2026-04-03T00:00:00', price: 90, volume: 10 },
          { time: '2026-04-10T00:00:00', price: 100, volume: 20 },
        ],
      },
    } as never)

    render(
      <MemoryRouter initialEntries={['/cs2/item/1']}><ToastProvider>
        <Routes>
          <Route path="/cs2/item/:id" element={<Cs2ItemDetail />} />
        </Routes>
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('AK-47 红线').length).toBeGreaterThan(0)
    })
    expect(screen.getByText('价格走势')).toBeInTheDocument()
    expect(screen.getByText('AI 预测')).toBeInTheDocument()
  })

  it('shows 404 when item not found', async () => {
    mocked.itemDetail.mockRejectedValue(new Error('404'))
    mocked.itemKline.mockRejectedValue(new Error('404'))

    render(
      <MemoryRouter initialEntries={['/cs2/item/99999']}><ToastProvider>
        <Routes>
          <Route path="/cs2/item/:id" element={<Cs2ItemDetail />} />
        </Routes>
      </ToastProvider></MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('饰品不存在')).toBeInTheDocument()
    })
  })
})
