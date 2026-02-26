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
}
