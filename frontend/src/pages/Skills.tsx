import { useEffect, useState } from 'react'
import { Cpu, Plus, Trash2, ChevronDown, ChevronUp, Zap } from 'lucide-react'
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

const typeLabels: Record<string, { label: string; color: string }> = {
  scorer: { label: '评分器', color: 'bg-primary/10 text-primary' },
  monitor: { label: '监控器', color: 'bg-warning/10 text-warning' },
  analyzer: { label: '分析器', color: 'bg-success/10 text-success' },
  generator: { label: '生成器', color: 'bg-danger/10 text-danger' },
}

const TEMPLATES = [
  {
    name: '自定义评分器',
    slug: 'custom_scorer',
    description: '根据自定义条件对新闻或数据进行评分',
    skill_type: 'scorer',
    config: { criteria: [{ indicator: '指标名称', condition: '> 阈值', weight: 50 }], output: '评级(A/B/C) + 理由' },
  },
  {
    name: '自定义监控器',
    slug: 'custom_monitor',
    description: '监控特定指标并在满足条件时触发预警',
    skill_type: 'monitor',
    config: { indicators: [{ name: '指标名称', warning: '预警条件' }], trigger_rules: { '条件描述': '操作建议' } },
  },
  {
    name: '自定义分析器',
    slug: 'custom_analyzer',
    description: '对市场数据进行多维度分析',
    skill_type: 'analyzer',
    config: { indicators: [{ name: '指标名称', condition: '分析条件' }], output: '分析结论 + 操作建议' },
  },
]

export default function Skills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

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

  const builtinSkills = skills.filter((s) => s.is_builtin)
  const customSkills = skills.filter((s) => !s.is_builtin)

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
        <>
          {/* Built-in Skills */}
          {builtinSkills.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-1.5">
                <Zap size={14} /> 内置投研 Skills ({builtinSkills.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {builtinSkills.map((skill) => (
                  <SkillCard
                    key={skill.id} skill={skill}
                    expanded={expandedId === skill.id}
                    onToggleExpand={() => setExpandedId(expandedId === skill.id ? null : skill.id)}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Custom Skills */}
          {customSkills.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-secondary mb-3">自定义 Skills ({customSkills.length})</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {customSkills.map((skill) => (
                  <SkillCard
                    key={skill.id} skill={skill}
                    expanded={expandedId === skill.id}
                    onToggleExpand={() => setExpandedId(expandedId === skill.id ? null : skill.id)}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function SkillCard({ skill, expanded, onToggleExpand, onToggle, onDelete }: {
  skill: Skill
  expanded: boolean
  onToggleExpand: () => void
  onToggle: (s: Skill) => void
  onDelete: (id: number) => void
}) {
  const typeInfo = typeLabels[skill.skill_type] || { label: skill.skill_type, color: 'bg-bg text-text-secondary' }

  const renderConfigPreview = () => {
    const config = skill.config
    const indicators = (config.indicators || config.criteria) as Array<Record<string, unknown>> | undefined
    if (!indicators || !Array.isArray(indicators)) return null
    return (
      <div className="mt-3 space-y-1.5">
        {indicators.slice(0, expanded ? undefined : 3).map((ind, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-primary mt-1.5" />
            <span className="text-text-secondary">
              <span className="font-medium text-text">{(ind.name || ind.indicator || ind.condition) as string}</span>
              {ind.warning && <span> — {ind.warning as string}</span>}
              {ind.condition && ind.name && <span> — {ind.condition as string}</span>}
              {ind.weight && <span className="ml-1 text-primary">(权重 {ind.weight as number}%)</span>}
            </span>
          </div>
        ))}
        {!expanded && indicators.length > 3 && (
          <p className="text-xs text-primary cursor-pointer" onClick={onToggleExpand}>
            ... 还有 {indicators.length - 3} 项
          </p>
        )}
      </div>
    )
  }

  return (
    <div className={`bg-card rounded-xl border border-border p-5 transition-all ${!skill.is_enabled ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Cpu size={18} className="text-primary" />
          <h3 className="font-semibold text-sm">{skill.name}</h3>
          {skill.is_builtin && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium">内置</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggle(skill)}
            className={`relative w-10 h-5 rounded-full transition-colors ${skill.is_enabled ? 'bg-success' : 'bg-gray-300'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${skill.is_enabled ? 'left-5' : 'left-0.5'}`} />
          </button>
          {!skill.is_builtin && (
            <button onClick={() => onDelete(skill.id)} className="text-text-secondary hover:text-danger"><Trash2 size={14} /></button>
          )}
        </div>
      </div>

      <p className="text-xs text-text-secondary mb-2">{skill.description}</p>

      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs px-2 py-0.5 rounded-full ${typeInfo.color}`}>{typeInfo.label}</span>
        <span className="text-xs text-text-secondary font-mono">{skill.slug}</span>
      </div>

      {renderConfigPreview()}

      <button onClick={onToggleExpand} className="flex items-center gap-1 mt-3 text-xs text-primary hover:underline">
        {expanded ? <><ChevronUp size={12} /> 收起详情</> : <><ChevronDown size={12} /> 展开详情</>}
      </button>

      {expanded && (
        <pre className="mt-3 p-3 bg-bg rounded-lg text-xs overflow-auto max-h-64 font-mono">
          {JSON.stringify(skill.config, null, 2)}
        </pre>
      )}
    </div>
  )
}

function CreateSkillForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '', slug: '', description: '', skill_type: 'scorer',
    config: '{\n  "criteria": []\n}',
  })
  const [error, setError] = useState('')

  const applyTemplate = (tpl: typeof TEMPLATES[0]) => {
    setForm({
      name: tpl.name,
      slug: tpl.slug + '_' + Date.now().toString(36),
      description: tpl.description,
      skill_type: tpl.skill_type,
      config: JSON.stringify(tpl.config, null, 2),
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const config = JSON.parse(form.config)
      await skillsApi.create({ ...form, config })
      onCreated()
    } catch (err) {
      if (err instanceof SyntaxError) setError('配置 JSON 格式错误')
      else setError('创建失败')
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5 mb-6">
      <h3 className="font-semibold mb-4">创建新 Skill</h3>

      {/* Templates */}
      <div className="mb-4">
        <p className="text-xs font-medium text-text-secondary mb-2">快速模板：</p>
        <div className="flex flex-wrap gap-2">
          {TEMPLATES.map((tpl) => (
            <button key={tpl.slug} onClick={() => applyTemplate(tpl)}
              className="px-3 py-1.5 text-xs rounded-lg border border-border hover:bg-bg transition-colors">
              {tpl.name}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit}>
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
              className="w-full px-3 py-2 rounded-lg border border-border text-sm">
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
            rows={8} className="w-full px-3 py-2 rounded-lg border border-border text-sm font-mono" />
        </div>
        {error && <p className="text-danger text-sm mb-3">{error}</p>}
        <div className="flex gap-2">
          <button type="submit" className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-dark">创建</button>
          <button type="button" onClick={onCreated} className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-bg">取消</button>
        </div>
      </form>
    </div>
  )
}
