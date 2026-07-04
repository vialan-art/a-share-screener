import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Save, RotateCcw, Settings2, Key, Database, Globe } from 'lucide-react'
import { fetchSettings, updateSettings, resetSettings } from '../services/api'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

const settingGroups = [
  {
    title: 'AI 助手',
    icon: Key,
    keys: ['ai_base_url', 'ai_api_key', 'ai_model'],
  },
  {
    title: '数据源',
    icon: Database,
    keys: ['data_provider', 'max_stocks', 'market_region', 'tushare_token'],
  },
  {
    title: '系统',
    icon: Settings2,
    keys: ['scheduler_time', 'database_url'],
  },
]

const fieldLabels: Record<string, string> = {
  ai_base_url: 'API Base URL',
  ai_api_key: 'API Key',
  ai_model: '模型',
  data_provider: '数据源',
  max_stocks: '最大股票数',
  scheduler_time: '定时时间',
  database_url: '数据库 URL',
  market_region: '默认市场',
  tushare_token: 'Tushare Token',
}

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, { value: string; description: string }>>({})
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    const data = await fetchSettings()
    setSettings(data)
  }

  async function handleSave() {
    setLoading(true)
    const payload: Record<string, string> = {}
    Object.entries(settings).forEach(([key, item]) => {
      payload[key] = item.value
    })
    await updateSettings(payload)
    setSaved(true)
    setLoading(false)
    setTimeout(() => setSaved(false), 2000)
  }

  async function handleReset() {
    if (!confirm('确定要重置所有设置为默认值吗？')) return
    await resetSettings()
    await loadSettings()
  }

  function updateValue(key: string, value: string) {
    setSettings((prev) => ({
      ...prev,
      [key]: { ...prev[key], value },
    }))
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-10 max-w-4xl"
    >
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">Configuration</p>
          <h2 className="font-serif text-4xl text-sumi">设置</h2>
        </div>
        <div className="flex gap-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleReset}
            className="btn-secondary inline-flex items-center gap-2"
          >
            <RotateCcw size={14} strokeWidth={1.5} />
            重置
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleSave}
            disabled={loading}
            className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
          >
            <Save size={14} strokeWidth={1.5} />
            {loading ? '保存中' : saved ? '已保存' : '保存设置'}
          </motion.button>
        </div>
      </motion.div>

      {settingGroups.map((group) => (
        <motion.div
          key={group.title}
          variants={itemVariants}
          className="glass-card rounded-2xl p-8"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-ink-100 flex items-center justify-center">
              <group.icon size={18} strokeWidth={1.5} className="text-ink-600" />
            </div>
            <h3 className="font-serif text-xl text-sumi">{group.title}</h3>
          </div>
          <div className="space-y-6">
            {group.keys.map((key) => {
              const item = settings[key]
              if (!item) return null
              return (
                <div key={key} className="space-y-2">
                  <label className="text-xs text-ink-600 font-medium flex items-center gap-2">
                    {fieldLabels[key] || key}
                  </label>
                  {key === 'data_provider' || key === 'market_region' ? (
                    <select
                      value={item.value}
                      onChange={(e) => updateValue(key, e.target.value)}
                      className="w-full bg-white/50 border border-ink-200/60 rounded-xl px-4 py-3 text-sm text-sumi focus:outline-none focus:border-moss/60 transition-colors"
                    >
                      {key === 'data_provider' && (
                        <>
                          <option value="mock">Mock（模拟数据）</option>
                          <option value="akshare">AkShare（A 股真实数据）</option>
                          <option value="us">US（美股 Yahoo Finance）</option>
                        </>
                      )}
                      {key === 'market_region' && (
                        <>
                          <option value="cn">A 股</option>
                          <option value="us">美股</option>
                        </>
                      )}
                    </select>
                  ) : (
                    <input
                      type={key.includes('api_key') || key.includes('token') ? 'password' : 'text'}
                      value={item.value}
                      onChange={(e) => updateValue(key, e.target.value)}
                      placeholder={item.description}
                      className="w-full bg-white/50 border border-ink-200/60 rounded-xl px-4 py-3 text-sm text-sumi placeholder:text-ink-400 focus:outline-none focus:border-moss/60 transition-colors"
                    />
                  )}
                  <p className="text-[10px] text-ink-400">{item.description}</p>
                </div>
              )
            })}
          </div>
        </motion.div>
      ))}

      <motion.div variants={itemVariants} className="marble-card rounded-2xl p-6">
        <div className="flex items-start gap-3">
          <Globe size={18} className="text-ink-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-ink-700 mb-1">配置说明</p>
            <p className="text-xs text-ink-500 leading-relaxed">
              修改数据源后，点击概览页的「运行选股」即可生效。AI 助手需要填写兼容 OpenAI 的 Base URL 和 API Key 后才会启用。
              数据库 URL 留空表示使用默认 SQLite。
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
