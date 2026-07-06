import { motion, AnimatePresence } from 'framer-motion'
import { useState, useRef, useEffect } from 'react'
import { advisorChat } from '../services/api'
import { Send, Sparkles, Bot, User } from 'lucide-react'
import DissolveCard from '../components/DissolveCard'

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

function SectionHeader({ number, label, title }: { number: string; label: string; title: string }) {
  return (
    <div className="mb-6">
      <p className="editorial-label mb-3">( {number} ) · {label}</p>
      <h2 className="font-display text-4xl lg:text-5xl text-slate-50">{title}</h2>
    </div>
  )
}

const suggestions = [
  'ROE 和 ROA 有什么区别？',
  '为什么审计意见是红线？',
  'PE 越低越好吗？',
  '这个评分系统是怎么工作的？',
]

export default function Advisor() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '你好，我是你的投资学习顾问。\\n\\n你可以问我关于财务指标、选股逻辑、行业分析的问题。我会用简单的方式解释，并区分事实与推断。',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(text?: string) {
    const userContent = text || input
    if (!userContent.trim()) return

    const userMsg: Message = { role: 'user', content: userContent }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const history = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const reply = await advisorChat(history)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply.content || '（AI 未返回内容）' },
      ])
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '调用 AI 顾问失败。请确认后端已配置 AI_ADVISOR_ENABLED=true 和正确的 API Key。',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="h-[calc(100vh-140px)] flex flex-col pb-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-6">
        <SectionHeader number="02" label="AI Advisor" title="投资顾问" />
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Sparkles size={14} className="text-cyan-300" />
          基于 OpenAI 兼容接口
        </div>
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="flex-1 flex flex-col"
      >
        <DissolveCard className="flex-1 liquid-glass flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            <AnimatePresence>
              {messages.map((msg, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 liquid-glass ${
                      msg.role === 'user' ? 'text-slate-600' : 'text-cyan-300'
                    }`}
                  >
                    {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                  </div>

                  <div
                    className={`max-w-[80%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-slate-900 text-slate-50 rounded-tr-sm'
                        : 'bg-slate-800/70 text-slate-200 rounded-tl-sm backdrop-blur-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-4"
              >
                <div className="w-9 h-9 rounded-full liquid-glass text-cyan-300 flex items-center justify-center">
                  <Bot size={14} />
                </div>
                <div className="px-5 py-3.5 rounded-2xl rounded-tl-sm bg-slate-800/70 backdrop-blur-sm">
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-slate-400"
                        animate={{ y: [0, -6, 0] }}
                        transition={{
                          duration: 0.6,
                          repeat: Infinity,
                          delay: i * 0.1,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-slate-700 p-6">
            <div className="flex flex-wrap gap-2 mb-4">
              {suggestions.map((suggestion) => (
                <motion.button
                  key={suggestion}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleSend(suggestion)}
                  disabled={loading}
                  className="text-xs px-3 py-1.5 rounded-full glass-float text-slate-600 hover:bg-slate-800 transition-colors"
                >
                  {suggestion}
                </motion.button>
              ))}
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="输入你的问题..."
                className="flex-1 glass-select"
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-slate-900 text-slate-50 rounded-xl hover:bg-slate-950 transition-colors disabled:opacity-40"
              >
                <Send size={16} strokeWidth={1.5} />
              </motion.button>
            </div>
          </div>
        </DissolveCard>
      </motion.div>
    </motion.div>
  )
}
