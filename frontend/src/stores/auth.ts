import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UserInfo {
  id: number
  username: string
}

interface AuthState {
  token: string
  user: UserInfo | null
  setAuth: (token: string, user: UserInfo) => void
  logout: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: '',
      user: null,
      setAuth: (token: string, user: UserInfo) => set({ token, user }),
      logout: () => set({ token: '', user: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: 'news-agent-auth' }
  )
)
