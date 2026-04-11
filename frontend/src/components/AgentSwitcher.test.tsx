import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import AgentSwitcher from './AgentSwitcher'
import { useAgentStore } from '@/stores/agent'
import { AGENTS } from '@/config/agents'

// Helper: 显示当前 URL，用于验证 navigate 行为
function LocationDisplay() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}</div>
}

function renderSwitcher(initialRoute = '/invest') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <AgentSwitcher />
      <LocationDisplay />
    </MemoryRouter>,
  )
}

describe('AgentSwitcher', () => {
  beforeEach(() => {
    // 重置 Zustand store 到默认
    useAgentStore.setState({ currentAgentId: 'investment' })
  })

  it('renders one button per agent', () => {
    renderSwitcher()
    AGENTS.forEach((agent) => {
      expect(screen.getByRole('button', { name: new RegExp(`切换到 ${agent.name}`) })).toBeInTheDocument()
    })
  })

  it('shows 3 agents in grid layout', () => {
    renderSwitcher()
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBe(AGENTS.length)
    expect(AGENTS.length).toBe(3)
  })

  it('displays current agent description', () => {
    renderSwitcher()
    const current = AGENTS.find((a) => a.id === 'investment')!
    expect(screen.getByText(current.description)).toBeInTheDocument()
  })

  it('marks current agent as pressed (aria-pressed=true)', () => {
    renderSwitcher()
    const investBtn = screen.getByRole('button', { name: /切换到 投研 Agent/ })
    expect(investBtn).toHaveAttribute('aria-pressed', 'true')

    const techBtn = screen.getByRole('button', { name: /切换到 技术信息 Agent/ })
    expect(techBtn).toHaveAttribute('aria-pressed', 'false')
  })

  it('single click switches agent and navigates', async () => {
    const user = userEvent.setup()
    renderSwitcher('/invest')

    // 初始在 investment
    expect(useAgentStore.getState().currentAgentId).toBe('investment')

    // 单击 CS2 按钮
    const cs2Btn = screen.getByRole('button', { name: /切换到 CS2 饰品市场/ })
    await user.click(cs2Btn)

    // Store 已切换
    expect(useAgentStore.getState().currentAgentId).toBe('cs2_market')
    // URL 已跳转到 /cs2
    expect(screen.getByTestId('location').textContent).toBe('/cs2')
  })

  it('does not re-navigate when clicking the already-active agent', async () => {
    const user = userEvent.setup()
    renderSwitcher('/invest/news')  // 初始在子路径

    const investBtn = screen.getByRole('button', { name: /切换到 投研 Agent/ })
    await user.click(investBtn)

    // 点击当前 agent 时不应改变路径
    expect(screen.getByTestId('location').textContent).toBe('/invest/news')
    expect(useAgentStore.getState().currentAgentId).toBe('investment')
  })

  it('updates description when switching agents', async () => {
    const user = userEvent.setup()
    renderSwitcher()

    const cs2Agent = AGENTS.find((a) => a.id === 'cs2_market')!
    const cs2Btn = screen.getByRole('button', { name: /切换到 CS2 饰品市场/ })
    await user.click(cs2Btn)

    expect(screen.getByText(cs2Agent.description)).toBeInTheDocument()
  })

  it('exposes title attribute for tooltip', () => {
    renderSwitcher()
    const techBtn = screen.getByRole('button', { name: /切换到 技术信息 Agent/ })
    const title = techBtn.getAttribute('title')
    expect(title).toContain('技术信息 Agent')
    expect(title).toContain('—')
  })

  it('switches between all 3 agents successfully', async () => {
    const user = userEvent.setup()
    renderSwitcher()

    // 切到 tech
    await user.click(screen.getByRole('button', { name: /切换到 技术信息 Agent/ }))
    expect(useAgentStore.getState().currentAgentId).toBe('tech_info')
    expect(screen.getByTestId('location').textContent).toBe('/tech')

    // 切到 cs2
    await user.click(screen.getByRole('button', { name: /切换到 CS2 饰品市场/ }))
    expect(useAgentStore.getState().currentAgentId).toBe('cs2_market')
    expect(screen.getByTestId('location').textContent).toBe('/cs2')

    // 切回 invest
    await user.click(screen.getByRole('button', { name: /切换到 投研 Agent/ }))
    expect(useAgentStore.getState().currentAgentId).toBe('investment')
    expect(screen.getByTestId('location').textContent).toBe('/invest')
  })
})

describe('useAgentStore persistence', () => {
  it('persists currentAgentId to localStorage', async () => {
    useAgentStore.setState({ currentAgentId: 'cs2_market' })
    // Zustand persist 应该写入 localStorage
    await new Promise((resolve) => setTimeout(resolve, 0))
    const stored = localStorage.getItem('news-agent-current')
    expect(stored).toBeTruthy()
    const parsed = JSON.parse(stored!)
    expect(parsed.state.currentAgentId).toBe('cs2_market')
  })

  it('defaults to investment on fresh state', () => {
    localStorage.clear()
    useAgentStore.setState({ currentAgentId: 'investment' })
    expect(useAgentStore.getState().currentAgentId).toBe('investment')
  })
})
