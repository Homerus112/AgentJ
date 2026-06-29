import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Pencil } from 'lucide-react'
import type { Message } from '@/store/chat'

const AGENT_COLORS: Record<string, string> = {
  dev: 'text-green-400', planner: 'text-blue-400', writer: 'text-yellow-400',
  news: 'text-orange-400', career: 'text-red-400', brand: 'text-pink-400',
  research: 'text-purple-400', vision: 'text-cyan-400', general: 'text-indigo-400',
  coach: 'text-amber-400', knowledge: 'text-teal-400',
}

interface Props {
  message: Message
  /** 편집 버튼 클릭 시 호출 — ChatWindow에서 store 수정 + InputBar 주입 처리 */
  onEdit?: (id: string) => void
}

export default function MessageBubble({ message, onEdit }: Props) {
  const { id, role, content, agent, timestamp } = message
  const isUser    = role === 'user'
  const isThinking= role === 'thinking'
  const [hovered, setHovered] = useState(false)

  if (isThinking) {
    return (
      <div className="flex items-center gap-2 px-4 py-1">
        <div className="flex gap-1">{[0,1,2].map(i => (
          <div key={i} className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
        ))}</div>
        <span className="text-xs text-[#555]">{content}</span>
      </div>
    )
  }

  const handleEditClick = () => {
    onEdit?.(id)
  }

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} px-4 py-1`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className={`max-w-[80%] relative ${isUser ? 'order-1' : 'order-2'}`}>
        {!isUser && agent && (
          <span className={`text-[10px] mb-1 block ${AGENT_COLORS[agent] ?? 'text-[#666]'}`}>
            {agent} agent
          </span>
        )}
        <div className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed selectable
          ${isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-[#1a1a1a] text-[#e0e0e0] border border-[#2a2a2a] rounded-tl-sm'}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}
              components={{
                code: ({ children, className }) => {
                  const isBlock = className?.includes('language-')
                  return isBlock
                    ? <pre className="bg-[#0a0a0a] rounded-lg p-3 mt-2 overflow-x-auto text-xs"><code>{children}</code></pre>
                    : <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-indigo-300">{children}</code>
                },
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
                h3: ({ children }) => <h3 className="font-semibold text-white mt-3 mb-1">{children}</h3>,
              }}>
              {content}
            </ReactMarkdown>
          )}
        </div>

        {/* 편집 버튼 — 사용자 메시지 hover 시 말풍선 왼쪽에 표시 */}
        {isUser && hovered && onEdit && (
          <button
            onClick={handleEditClick}
            title="메시지 수정 후 재전송"
            className="absolute -left-8 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-[#555] hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors"
          >
            <Pencil size={13} />
          </button>
        )}

        <p className="text-[9px] text-[#444] mt-0.5 px-1">{new Date(timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</p>
      </div>
    </div>
  )
}
