import client from './client'

export const techApi = {
  getArticles: (params?: Record<string, string | number>) =>
    client.get('/tech/articles', { params }),
  getDashboard: () =>
    client.get('/tech/dashboard'),
  getSources: () =>
    client.get('/tech/sources'),
}
