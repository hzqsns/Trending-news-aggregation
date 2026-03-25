import client from './client'

export const dashboardApi = {
  getOverview: () => client.get('/dashboard/overview'),
  getSentimentHistory: (days = 7) => client.get(`/dashboard/sentiment/history?days=${days}`),
  getStats: () => client.get('/dashboard/stats'),
}

export const articlesApi = {
  list: (params: Record<string, unknown> = {}) => client.get('/articles/', { params }),
  trending: (limit = 10) => client.get('/articles/trending', { params: { limit } }),
  get: (id: number) => client.get(`/articles/${id}`),
  sources: () => client.get('/articles/sources'),
  categories: () => client.get('/articles/categories'),
}

export const reportsApi = {
  list: (params: Record<string, unknown> = {}) => client.get('/reports/', { params }),
  latest: (type?: string) => client.get('/reports/latest', { params: { report_type: type } }),
  get: (id: number) => client.get(`/reports/${id}`),
  generate: (report_type: 'morning' | 'evening') => client.post('/reports/generate', { report_type }),
  listByType: (report_type: string, page_size = 7) =>
    client.get('/reports/', { params: { report_type, page_size } }),
  generateTwitterDigest: () => client.post('/reports/generate-twitter-digest'),
}

export const alertsApi = {
  list: (params: Record<string, unknown> = {}) => client.get('/alerts/', { params }),
  active: () => client.get('/alerts/active'),
  resolve: (id: number) => client.put(`/alerts/${id}/resolve`),
}

export const skillsApi = {
  list: () => client.get('/skills/'),
  get: (id: number) => client.get(`/skills/${id}`),
  create: (data: Record<string, unknown>) => client.post('/skills/', data),
  update: (id: number, data: Record<string, unknown>) => client.put(`/skills/${id}`, data),
  delete: (id: number) => client.delete(`/skills/${id}`),
}

export const settingsApi = {
  list: (category?: string) => client.get('/settings/', { params: { category } }),
  update: (key: string, value: string) => client.put(`/settings/${key}`, { value }),
  batchUpdate: (settings: Record<string, string>) => client.put('/settings/', { settings }),
  categories: () => client.get('/settings/categories'),
  aiProviders: () => client.get('/settings/ai-providers'),
  testAi: () => client.post('/settings/test-ai'),
}

export const twitterApi = {
  listHandles: () => client.get('/twitter/handles'),
  addHandle: (handle: string) => client.post('/twitter/handles', { handle }),
  removeHandle: (handle: string) => client.delete(`/twitter/handles/${handle}`),
  manualFetch: () => client.post('/twitter/fetch'),
  testAuth: () => client.post('/twitter/test-auth'),
  importCookies: (cookies: string) => client.post('/twitter/import-cookies', { cookies }),
}

export const calendarApi = {
  list: (params: { start?: string; end?: string; event_type?: string; days?: number } = {}) =>
    client.get('/calendar/', { params }),
  create: (data: {
    title: string
    event_type: string
    event_date: string
    event_time?: string
    description?: string
    importance?: string
    meta?: Record<string, unknown>
  }) => client.post('/calendar/', data),
  update: (id: number, data: Partial<{ title: string; event_date: string; event_time: string; description: string; importance: string }>) =>
    client.put(`/calendar/${id}`, data),
  remove: (id: number) => client.delete(`/calendar/${id}`),
  seed: () => client.post('/calendar/seed'),
}

export const bookmarksApi = {
  list: (params: Record<string, unknown> = {}) => client.get('/bookmarks/', { params }),
  create: (article_id: number, note?: string, tags?: string[]) =>
    client.post('/bookmarks/', { article_id, note: note ?? null, tags: tags ?? [] }),
  update: (article_id: number, note: string | null, tags: string[]) =>
    client.put(`/bookmarks/${article_id}`, { note, tags }),
  remove: (article_id: number) => client.delete(`/bookmarks/${article_id}`),
  tags: () => client.get('/bookmarks/tags'),
  status: (article_ids: number[]) =>
    client.get('/bookmarks/status', { params: { article_ids: article_ids.join(',') } }),
}

export const macroApi = {
  getAll: () => client.get('/macro/indicators'),
  refresh: () => client.post('/macro/refresh'),
}

export const historicalEventsApi = {
  list: (params: { category?: string; search?: string } = {}) =>
    client.get('/historical-events/', { params }),
  create: (data: {
    title: string
    category: string
    date_range: string
    market_impact: string
    description?: string
    key_metrics?: Array<{ label: string; value: string }>
  }) => client.post('/historical-events/', data),
  remove: (id: number) => client.delete(`/historical-events/${id}`),
  seed: () => client.post('/historical-events/seed'),
}
