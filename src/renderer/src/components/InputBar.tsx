import { useRef, useState, useEffect, useCallback, KeyboardEvent } from 'react'
import { Send, Loader2, Paperclip, X, Square } from 'lucide-react'
import QuickActionBar from './QuickActionBar'
import { uploadFile } from '@/lib/api'

interface Command { cmd: string; label: string; icon: string }

const ALL_COMMANDS: Command[] = [
  { cmd: '/stats',        label: '에이전트 사용 통계',           icon: '📊' },
  { cmd: '/memory',       label: 'J가 기억하는 내용 보기',       icon: '🧠' },
  { cmd: '/tasks',        label: '할 일 목록',                   icon: '✅' },
  { cmd: '/schedule',     label: '일정 보기',                    icon: '📅' },
  { cmd: '/career',       label: '커리어 현황 요약',             icon: '🎯' },
  { cmd: '/career gap',   label: '스킬 갭 분석',                 icon: '📈' },
  { cmd: '/career brief', label: '면접 브리핑',                  icon: '🗂️' },
  { cmd: '/brand',        label: 'LinkedIn/Instagram 초안',      icon: '📣' },
  { cmd: '/reflect',      label: '오늘 회고 작성',               icon: '📝' },
  { cmd: '/weekly',       label: '주간 리뷰 생성',               icon: '📆' },
  { cmd: '/learning',     label: '학습 진도 통계',               icon: '🎓' },
  { cmd: '/coach',        label: '목표 코치 리뷰',               icon: '🏆' },
  { cmd: '/compress',     label: '장기 메모리 압축',             icon: '💾' },
  { cmd: '/remember',     label: '영구 메모 저장',               icon: '📌' },
  { cmd: '/help',         label: '전체 명령어 보기',             icon: '❓' },
]

interface UploadedFile { name: string; content: string; chars: number }

interface Props {
  onSend:    (text: string) => void
  onCancel:  () => void
  isLoading: boolean
  editText?: string   // 편집 원문
  editKey?:  number   // 같은 원문 재편집 감지 (값 변경 시 useEffect 재실행)
}

export default function InputBar({ onSend, onCancel, isLoading, editText, editKey }: Props) {
  const [input,        setInput]        = useState('')
  const [suggestions,  setSuggestions]  = useState<Command[]>([])
  const [activeIdx,    setActiveIdx]    = useState(0)
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null)
  const [uploading,    setUploading]    = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // editKey가 바뀔 때마다 editText를 InputBar에 주입 (같은 텍스트 재편집도 동작)
  useEffect(() => {
    if (editKey && editText) {
      setInput(editText)
      setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }, [editKey]) // editText는 의도적으로 deps 제외 (editKey와 항상 같이 변경됨)

  useEffect(() => {
    if (input.startsWith('/')) {
      const q = input.toLowerCase()
      setSuggestions(ALL_COMMANDS.filter(c => c.cmd.startsWith(q) || c.label.includes(input.slice(1))))
      setActiveIdx(0)
    } else { setSuggestions([]) }
  }, [input])

  const selectCommand = useCallback((cmd: Command) => {
    setInput(cmd.cmd + ' '); setSuggestions([]); textareaRef.current?.focus()
  }, [])

  // 파일 업로드 처리
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await uploadFile(file)
      setUploadedFile(result)
    } catch {
      alert('파일 업로드 실패')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [])

  // 드래그&드롭 지원
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (!file) return
    setUploading(true)
    try {
      const result = await uploadFile(file)
      setUploadedFile(result)
    } catch {
      alert('파일 업로드 실패')
    } finally { setUploading(false) }
  }, [])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if ((!text && !uploadedFile) || isLoading) return

    let finalMessage = text

    // 파일 내용이 있으면 컨텍스트로 주입
    if (uploadedFile) {
      const fileContext = `[첨부 파일: ${uploadedFile.name}]\n\`\`\`\n${uploadedFile.content}\n\`\`\``
      finalMessage = text
        ? `${fileContext}\n\n${text}`
        : `${fileContext}\n\n위 파일 내용을 분석하고 핵심 내용을 요약해줘.`
      setUploadedFile(null)
    }

    onSend(finalMessage)
    setInput('')
    setSuggestions([])
  }, [input, isLoading, onSend, uploadedFile])

  const handleFill = useCallback((command: string) => {
    setInput(command); textareaRef.current?.focus()
  }, [])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i+1, suggestions.length-1)); return }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(i-1, 0)); return }
      if (e.key === 'Tab' || (e.key === 'Enter' && input.startsWith('/'))) { e.preventDefault(); selectCommand(suggestions[activeIdx]); return }
      if (e.key === 'Escape')    { setSuggestions([]); return }
    }
    // Esc로 요청 취소
    if (e.key === 'Escape' && isLoading) { e.preventDefault(); onCancel(); return }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div
      className="border-t border-[#2e2e2e] relative"
      onDragOver={e => e.preventDefault()}
      onDrop={handleDrop}
    >
      <QuickActionBar onSend={onSend} onFill={handleFill} isLoading={isLoading} />

      {/* 업로드된 파일 표시 */}
      {uploadedFile && (
        <div className="mx-4 mb-2 flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-3 py-1.5">
          <span className="text-sm">📄</span>
          <span className="text-xs text-indigo-300 flex-1 truncate">{uploadedFile.name}</span>
          <span className="text-[10px] text-[#555]">{uploadedFile.chars.toLocaleString()}자</span>
          <button onClick={() => setUploadedFile(null)} className="text-[#555] hover:text-[#aaa]">
            <X size={12} />
          </button>
        </div>
      )}

      <div className="px-4 pb-4 pt-1 relative">
        {suggestions.length > 0 && (
          <div className="absolute bottom-full left-4 right-4 mb-1 bg-[#1e1e1e] border border-[#333] rounded-xl overflow-hidden shadow-2xl z-50">
            <div className="px-3 py-1.5 text-[10px] text-[#555] border-b border-[#2a2a2a] uppercase tracking-wider">명령어 — Tab 또는 Enter로 선택</div>
            {suggestions.map((c, i) => (
              <button key={c.cmd} onMouseDown={e => { e.preventDefault(); selectCommand(c) }}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors
                  ${i === activeIdx ? 'bg-indigo-600/20 text-white' : 'text-[#aaa] hover:bg-[#2a2a2a]'}`}>
                <span className="text-base w-5 text-center shrink-0">{c.icon}</span>
                <span className="text-xs font-mono text-indigo-300 shrink-0 w-36">{c.cmd}</span>
                <span className="text-xs text-[#777] truncate">{c.label}</span>
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 bg-[#1e1e1e] border border-[#2e2e2e] rounded-xl px-3 py-2 focus-within:border-indigo-500 transition-colors">
          {/* 파일 첨부 버튼 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || isLoading}
            title="파일 첨부 (PDF, DOCX, TXT, 이미지)"
            className="p-1.5 rounded-lg text-[#555] hover:text-indigo-400 hover:bg-indigo-500/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
          >
            {uploading ? <Loader2 size={14} className="animate-spin text-indigo-400" /> : <Paperclip size={14} />}
          </button>

          <textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={uploadedFile ? '파일에 대해 질문하거나 Enter로 바로 분석...' : 'J에게 자유롭게 메시지 보내기... (/ 로 명령어, 파일 드래그&드롭 가능)'}
            rows={1} disabled={isLoading}
            className="flex-1 bg-transparent text-[#f0f0f0] placeholder-[#555] resize-none outline-none text-sm leading-relaxed max-h-32 overflow-y-auto selectable"
            style={{ minHeight: '24px' }} />

          {/* 로딩 중: 취소 버튼 / 대기 중: 전송 버튼 */}
          {isLoading ? (
            <button onClick={onCancel} title="요청 취소 (Esc)"
              className="p-1.5 rounded-lg bg-red-600/80 hover:bg-red-500 transition-colors shrink-0">
              <Square size={14} className="text-white" />
            </button>
          ) : (
            <button onClick={handleSend} disabled={!input.trim() && !uploadedFile}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0">
              <Send size={14} className="text-white" />
            </button>
          )}
        </div>
        <p className="text-[10px] text-[#444] mt-1 px-1">Enter 전송 · Shift+Enter 줄바꿈 · Esc 취소 · 📎 파일 첨부 · 드래그&드롭 지원</p>
      </div>

      {/* 히든 파일 인풋 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.pdf,.docx,.doc,.py,.js,.ts,.tsx,.json,.csv,.png,.jpg,.jpeg,.gif,.webp"
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  )
}
