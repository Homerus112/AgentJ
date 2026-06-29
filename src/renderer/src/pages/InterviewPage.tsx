import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, RefreshCw, Mic, CloudUpload } from 'lucide-react'
import { interviewChat, notionPush } from '@/lib/api'

interface Message { role: 'user' | 'assistant'; content: string }

const PRESETS = [
  { label: 'Google SWE', company: 'Google', role: 'Software Engineer', type: '행동+기술 면접' },
  { label: 'Meta PM', company: 'Meta', role: 'Product Manager', type: '행동+기획 면접' },
  { label: 'Amazon SDE', company: 'Amazon', role: 'SDE', type: '행동(리더십원칙)+기술' },
  { label: '스타트업 BE', company: '스타트업', role: 'Backend Engineer', type: '기술 집중' },
  { label: '커스텀', company: '', role: '', type: '' },
]

export default function InterviewPage() {
  const [phase,          setPhase]          = useState<'setup' | 'session'>('setup')
  const [preset,         setPreset]         = useState(PRESETS[0])
  const [customCompany,  setCustomCompany]  = useState('')
  const [customRole,     setCustomRole]     = useState('')
  const [customType,     setCustomType]     = useState('')
  const [messages,       setMessages]       = useState<Message[]>([])
  const [input,          setInput]          = useState('')
  const [loading,        setLoading]        = useState(false)
  const [notionSaving,   setNotionSaving]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const company  = preset.label === '커스텀' ? customCompany : preset.company
  const role     = preset.label === '커스텀' ? customRole    : preset.role
  const type     = preset.label === '커스텀' ? customType    : preset.type

  const startInterview = async () => {
    if (!company || !role) return
    setPhase('session')
    setLoading(true)
    const startMsg = `${company} ${role} 포지션 모의 면접을 시작해줘. 면접 유형: ${type || '행동+기술 혼합'}. 바로 첫 번째 질문을 해줘.`
    try {
      const r = await interviewChat(startMsg, [])
      setMessages([
        { role: 'user', content: startMsg },
        { role: 'assistant', content: r.response }
      ])
    } catch { setMessages([{ role: 'assistant', content: '면접 시작 오류. 서버를 확인해주세요.' }]) }
    finally { setLoading(false) }
  }

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return
    const newHistory = [...messages, { role: 'user' as const, content: text }]
    setMessages(newHistory)
    setInput('')
    setLoading(true)
    try {
      const history = newHistory.map(m => ({ role: m.role, content: m.content }))
      const r = await interviewChat(text, history)
      setMessages(prev => [...prev, { role: 'assistant', content: r.response }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '응답 오류가 발생했습니다.' }])
    } finally { setLoading(false) }
  }

  const saveToNotion = async () => {
    if (messages.length === 0) return
    setNotionSaving(true)
    const content = messages.map(m => `**${m.role === 'user' ? 'Jeremy' : '면접관 J'}:**\n${m.content}`).join('\n\n---\n\n')
    try {
      await notionPush(`면접 세션 — ${company} ${role} (${new Date().toLocaleDateString('ko-KR')})`, content, 'memo')
      alert('Notion에 저장됐습니다!')
    } catch { alert('Notion 저장 실패') }
    finally { setNotionSaving(false) }
  }

  const reset = () => {
    setPhase('setup')
    setMessages([])
    setInput('')
  }

  if (phase === 'setup') {
    return (
      <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">
        <h2 className="text-lg font-semibold text-white mb-2">🎤 면접 코치</h2>
        <p className="text-xs text-[#555] mb-6">AI 면접관과 실전 모의 면접 — 질문 → 답변 → 즉각 피드백</p>

        <div className="max-w-md">
          {/* 프리셋 선택 */}
          <p className="text-xs text-[#666] mb-2 font-medium">면접 유형 선택</p>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {PRESETS.map(p => (
              <button key={p.label}
                onClick={() => setPreset(p)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  preset.label === p.label
                    ? 'border-indigo-500 bg-indigo-500/10 text-white'
                    : 'border-[#2e2e2e] bg-[#1a1a1a] text-[#888] hover:border-[#444]'
                }`}>
                <p className="text-xs font-medium">{p.label}</p>
                {p.type && <p className="text-[10px] text-[#555] mt-0.5">{p.type}</p>}
              </button>
            ))}
          </div>

          {/* 커스텀 입력 */}
          {preset.label === '커스텀' && (
            <div className="space-y-2 mb-4">
              <input
                value={customCompany} onChange={e => setCustomCompany(e.target.value)}
                placeholder="회사명 (예: Kakao)"
                className="w-full bg-[#1e1e1e] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500"
              />
              <input
                value={customRole} onChange={e => setCustomRole(e.target.value)}
                placeholder="직무 (예: Backend Engineer)"
                className="w-full bg-[#1e1e1e] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500"
              />
              <input
                value={customType} onChange={e => setCustomType(e.target.value)}
                placeholder="면접 유형 (예: 행동+기술 혼합)"
                className="w-full bg-[#1e1e1e] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500"
              />
            </div>
          )}

          {/* 선택된 정보 요약 */}
          {company && role && (
            <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-3 mb-5">
              <p className="text-xs text-[#666]">면접 대상</p>
              <p className="text-sm text-white mt-0.5">{company} — {role}</p>
              {type && <p className="text-[11px] text-indigo-400 mt-0.5">{type}</p>}
            </div>
          )}

          <button
            onClick={startInterview}
            disabled={!company || !role}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
          >
            ▶ 면접 시작
          </button>

          <div className="mt-4 bg-[#111] border border-[#1e1e1e] rounded-xl p-3">
            <p className="text-[10px] text-[#555] leading-relaxed">
              💡 <strong className="text-[#444]">사용 방법:</strong> 면접관의 질문에 자연스럽게 답변하세요.
              답변 후 즉각 피드백과 개선안을 받을 수 있습니다.
              세션 종료 시 "종료" 또는 "끝"이라고 입력하면 최종 리포트를 생성합니다.
            </p>
          </div>
        </div>
      </div>
    )
  }

  // 면접 세션 화면
  return (
    <div className="flex-1 flex flex-col bg-[#0f0f0f] overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e1e1e] shrink-0">
        <div>
          <p className="text-sm font-medium text-white">🎤 {company} — {role}</p>
          <p className="text-[10px] text-[#555]">{type}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={saveToNotion}
            disabled={notionSaving || messages.length === 0}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#1e1e1e] hover:bg-[#2e2e2e] text-[#666] hover:text-indigo-400 text-[10px] border border-[#2e2e2e] transition-colors disabled:opacity-30"
          >
            <CloudUpload size={11} /> {notionSaving ? '저장 중...' : 'Notion 저장'}
          </button>
          <button onClick={reset}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#1e1e1e] hover:bg-[#2e2e2e] text-[#666] hover:text-[#aaa] text-[10px] border border-[#2e2e2e] transition-colors">
            <RefreshCw size={11} /> 새 세션
          </button>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.filter(m => !(m.role === 'user' && m.content.includes('모의 면접을 시작해줘'))).map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-indigo-600 text-white'
                : 'bg-[#1a1a1a] border border-[#2e2e2e] text-[#e0e0e0]'
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl px-4 py-3 flex items-center gap-2">
              <Loader2 size={13} className="text-indigo-400 animate-spin" />
              <span className="text-xs text-[#555]">면접관 답변 생성 중...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력 */}
      <div className="px-5 py-4 border-t border-[#1e1e1e] shrink-0">
        <div className="flex items-end gap-2 bg-[#1e1e1e] border border-[#2e2e2e] rounded-xl px-3 py-2 focus-within:border-indigo-500 transition-colors">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
            placeholder='답변을 입력하세요... (Enter 전송 · "종료" 입력 시 최종 리포트 생성)'
            rows={2}
            disabled={loading}
            className="flex-1 bg-transparent text-[#f0f0f0] placeholder-[#444] resize-none outline-none text-sm leading-relaxed"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 transition-colors shrink-0"
          >
            {loading ? <Loader2 size={14} className="text-white animate-spin" /> : <Send size={14} className="text-white" />}
          </button>
        </div>
        <p className="text-[10px] text-[#444] mt-1">"종료" 또는 "끝" 입력 → 최종 리포트 · Notion 저장 버튼으로 세션 내용 저장</p>
      </div>
    </div>
  )
}
