import client from './client'

export const cs2Api = {
  marketOverview: (period = '24h') =>
    client.get('/cs2/market/overview', { params: { period } }),
  marketRefresh: () =>
    client.post('/cs2/market/refresh'),
  hotItems: (limit = 10) =>
    client.get('/cs2/market/hot-items', { params: { limit } }),

  rankings: (params: Record<string, string | number | undefined>) =>
    client.get('/cs2/rankings', { params }),

  categories: () => client.get('/cs2/categories'),
  categoryTrend: (id: string, period = '7d') =>
    client.get(`/cs2/categories/${id}/trend`, { params: { period } }),
  categoryTopItems: (id: string, limit = 10) =>
    client.get(`/cs2/categories/${id}/top-items`, { params: { limit } }),

  itemDetail: (id: number) => client.get(`/cs2/items/${id}`),
  itemKline: (id: number, period = '7d') =>
    client.get(`/cs2/items/${id}/kline`, { params: { period } }),

  predictions: (params: Record<string, string | number | undefined>) =>
    client.get('/cs2/predictions', { params }),
  regeneratePrediction: (itemId: number, period = '7d') =>
    client.post('/cs2/predictions/regenerate', null, { params: { item_id: itemId, period } }),
  generateAllPredictions: (period = '7d', limit = 20) =>
    client.post('/cs2/predictions/generate-all', null, { params: { period, limit } }),

  watchlist: () => client.get('/cs2/watchlist'),
  addWatch: (itemId: number, targetPrice?: number, direction?: string) =>
    client.post('/cs2/watchlist', null, {
      params: { item_id: itemId, target_price: targetPrice, alert_direction: direction },
    }),
  updateWatch: (watchId: number, targetPrice?: number, direction?: string) =>
    client.put(`/cs2/watchlist/${watchId}`, null, {
      params: { target_price: targetPrice, alert_direction: direction },
    }),
  deleteWatch: (watchId: number) => client.delete(`/cs2/watchlist/${watchId}`),
  watchlistAlerts: (limit = 20) =>
    client.get('/cs2/watchlist/alerts', { params: { limit } }),
}

export interface Cs2Item {
  id: number
  market_hash_name: string
  display_name: string
  category: string
  subcategory: string | null
  rarity: string | null
  image_url: string | null
  is_tracked: boolean
}

export interface Cs2RankingItem {
  id: number
  name: string
  market_hash_name: string
  image_url: string | null
  category: string
  rarity: string | null
  current_price: number
  change_pct: number
  change_value: number
  volume: number
}

export interface Cs2Prediction {
  id: number
  item_id: number
  period: string
  direction: 'bullish' | 'bearish' | 'neutral'
  up_prob: number
  flat_prob: number
  down_prob: number
  confidence: number
  predicted_price: number | null
  reasoning: string | null
  factors: string[] | null
  generated_at: string | null
  item_name?: string
  item_category?: string
}
