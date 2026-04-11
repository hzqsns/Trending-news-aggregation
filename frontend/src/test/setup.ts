import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// 每个测试后清理 DOM
afterEach(() => {
  cleanup()
  // 清理 localStorage，防止 Zustand persist 跨测试污染
  localStorage.clear()
  // 清理 html data-agent 属性
  document.documentElement.removeAttribute('data-agent')
})
