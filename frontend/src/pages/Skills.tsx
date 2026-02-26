import { useEffect, useState } from 'react'
import { Cpu, Plus, Trash2 } from 'lucide-react'
import { skillsApi } from '@/api'

interface Skill {
  id: number
  name: string
  slug: string
  description: string | null
  skill_type: string
  config: Record<string, unknown>
  is_builtin: boolean
  is_enabled: boolean
}

const typeLabels: Record<string, string> = {
  scorer: '评分器',
  monitor: '监控器',
  analyzer: '分析器',
  generator: '生成器',
}

export default function Skills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const load = async () => {
    try {
      const resp = await skillsApi.list()
      setSkills(resp.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleToggle = async (skill: Skill) => {
    try {
      await skillsApi.update(skill.id, { is_enabled: !skill.is_enabled })
      load()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除此 Skill？')) return
    try {
      await skillsApi.delete(id)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Skills 决策框架</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors"
        >
          <Plus size={16} /> 新建 Skill
        </button>
      </div>

      {showCreate && <CreateSkillForm onCreated={() => { setShowCreate(false); load() }} />}

      {loading ? (
        <div className="p-8 text-center text-text-secondary">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {skills.map((skill) => (
            <div key={skill.id} className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Cpu size={18} className="text-primary" />
                  <h3 className="font-semibold text-sm">{skill.name}</h3>
                  {skill.is_builtin && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">内置</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(skill)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${skill.is_enabled ? 'bg-success' : 'bg-gray-300'}`}
                  >
                    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${skill.is_enabled ? 'left-5' : 'left-0.5'}`} />
                  </button>
                  {!skill.is_builtin && (
                    <button onClick={() => handleDelete(skill.id)} className="text-text-secondary hover:text-danger">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
              <p className="text-xs text-text-secondary mb-3">{skill.description}</p>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-bg">{typeLabels[skill.skill_type] || skill.skill_type}</span>
                <span className="text-xs text-text-secondary">{skill.slug}</span>
              </div>
              <details className="mt-3">
                <summary className="text-xs text-primary cursor-pointer">查看配置</summary>
                <pre className="mt-2 p-3 bg-bg rounded-lg text-xs overflow-auto max-h-48">
                  {JSON.stringify(skill.config, null, 2)}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CreateSkillForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '',
    slug: '',
    description: '',
    skill_type: 'scorer',
    config: '{\n  "criteria": []\n}',
  })
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const config = JSON.parse(form.config)
      await skillsApi.create({ ...form, config })
      onCreated()
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('配置 JSON 格式错误')
      } else {
        setError('创建失败')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-5 mb-6">
      <h3 className="font-semibold mb-4">创建新 Skill</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs font-medium mb-1">名称</label>
          <input value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg border border-border text-sm" required />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">标识 (slug)</label>
          <input value={form.slug} onChange={(e) => setForm(f => ({ ...f, slug: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg border border-border text-sm" required />
        </div>
        <div className="md:col-span-2">
          <label className="block text-xs font-medium mb-1">描述</label>
          <input value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg border border-border text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">类型</label>
          <select value={form.skill_type} onChange={(e) => setForm(f => ({ ...f, skill_type: e.target.value }))}
            className="w-full px-3 py-2 rounded-lg border border-border text-sm bg-white">
            <option value="scorer">评分器</option>
            <option value="monitor">监控器</option>
            <option value="analyzer">分析器</option>
            <option value="generator">生成器</option>
          </select>
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-xs font-medium mb-1">配置 (JSON)</label>
        <textarea value={form.config} onChange={(e) => setForm(f => ({ ...f, config: e.target.value }))}
          rows={6} className="w-full px-3 py-2 rounded-lg border border-border text-sm font-mono" />
      </div>
      {error && <p className="text-danger text-sm mb-3">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-dark">创建</button>
        <button type="button" onClick={onCreated} className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-bg">取消</button>
      </div>
    </form>
  )
}
