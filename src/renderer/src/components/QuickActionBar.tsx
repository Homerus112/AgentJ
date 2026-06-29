import { useState, useEffect, useRef } from 'react'
import { Plus, X, Check, ChevronLeft, ChevronRight, Pencil } from 'lucide-react'
import { getQuickActions, addQuickAction, deleteQuickAction, type QuickAction } from '@/lib/api'

interface Props { onSend: (cmd: string) => void; onFill: (cmd: string) => void; isLoading: boolean }

export default function QuickActionBar({ onSend, onFill, isLoading }: Props) {
  const [actions,      setActions]      = useState<QuickAction[]>([])
  const [editMode,     setEditMode]     = useState(false)
  const [isAdding,     setIsAdding]     = useState(false)
  const [newLabel,     setNewLabel]     = useState('')
  const [newIcon,      setNewIcon]      = useState('⚡')
  const [newCommand,   setNewCommand]   = useState('')
  const [newImmediate, setNewImmediate] = useState(true)
  const [saving,       setSaving]       = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getQuickActions().then(setActions).catch(() => {})
  }, [])

  function handleChipClick(a: QuickAction) {
    if (editMode || isLoading) return
    a.send_immediately ? onSend(a.command) : onFill(a.command + ' ')
  }

  async function handleAdd() {
    const label = newLabel.trim()
    const command = newCommand.trim()
    if (!label || !command) return
    setSaving(true)
    try {
      const created = await addQuickAction({
        label, icon: newIcon || '⚡', command, send_immediately: newImmediate,
      })
      setActions(p => [...p, created])
      setNewLabel(''); setNewIcon('⚡'); setNewCommand(''); setNewImmediate(true)
      setIsAdding(false)
    } catch { alert('추가 실패') } finally { setSaving(false) }
  }

  async function handleDelete(id: string) {
    try {
      await deleteQuickAction(id)
      setActions(p => p.filter(a => a.id !== id))
    } catch { alert('삭제 실패') }
  }

  function scroll(dir: 'left' | 'right') {
    scrollRef.current?.scrollBy({ left: dir === 'left' ? -120 : 120, behavior: 'smooth' })
  }

  function exitEdit() {
    setEditMode(false)
    setIsAdding(false)
    setNewLabel(''); setNewIcon('⚡'); setNewCommand('')
  }

  return (
    // pt-3: 편집 모드 삭제 버튼이 잘리지 않도록 위 여백 확보
    <div className="px-3 pt-3 pb-1 select-none">
      <div className="flex items-center gap-1">

        {/* 왼쪽 스크롤 */}
        <button onClick={() => scroll('left')}
          className="shrink-0 p-0.5 rounded text-[#444] hover:text-[#aaa] transition-colors">
          <ChevronLeft size={13} />
        </button>

        {/* 칩 목록 */}
        <div
          ref={scrollRef}
          className="flex items-center gap-1.5 overflow-x-auto flex-1 scrollbar-none"
          style={{ scrollbarWidth: 'none' }}
        >
          {actions.map((a) => (
            <div key={a.id} className="relative shrink-0 group">
              <button
                onClick={() => handleChipClick(a)}
                disabled={isLoading || editMode}
                title={a.command}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border whitespace-nowrap transition-all
                  ${editMode
                    ? 'border-red-500/30 bg-red-500/5 text-[#666] cursor-default pr-6'
                    : 'border-[#2e2e2e] bg-[#1a1a1a] text-[#999] hover:text-indigo-300 hover:border-indigo-500/60 hover:bg-indigo-500/5 disabled:opacity-40 disabled:cursor-not-allowed'
                  }`}
              >
                <span>{a.icon}</span>
                <span>{a.label}</span>
                {!a.send_immediately && <span className="text-[9px] text-[#555]">↩</span>}
              </button>

              {/* 삭제 버튼: 칩 안쪽 오른편에 인라인으로 표시 → overflow 잘림 없음 */}
              {editMode && (
                <button
                  onClick={() => handleDelete(a.id)}
                  title="삭제"
                  className="absolute right-1 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full
                    bg-red-500 hover:bg-red-400 text-white flex items-center justify-center transition-colors"
                >
                  <X size={8} />
                </button>
              )}
            </div>
          ))}

          {/* 추가 폼 — 편집 모드에서 + 버튼 클릭 시 표시 */}
          {isAdding && (
            <div className="flex items-center gap-1 shrink-0 bg-[#1e1e1e] border border-indigo-500/40 rounded-full px-2 py-0.5">
              <input
                type="text" value={newIcon} onChange={e => setNewIcon(e.target.value)}
                maxLength={2} className="w-6 bg-transparent text-center text-sm outline-none"
                placeholder="⚡"
              />
              <input
                type="text" value={newLabel} onChange={e => setNewLabel(e.target.value)}
                placeholder="이름"
                className="w-16 bg-transparent text-xs text-[#f0f0f0] outline-none placeholder-[#444]"
                onKeyDown={e => { if (e.key === 'Enter') handleAdd(); if (e.key === 'Escape') setIsAdding(false) }}
                autoFocus
              />
              <span className="text-[#444] text-xs">→</span>
              <input
                type="text" value={newCommand} onChange={e => setNewCommand(e.target.value)}
                placeholder="/command"
                className="w-28 bg-transparent text-xs text-indigo-300 outline-none placeholder-[#444] font-mono"
                onKeyDown={e => { if (e.key === 'Enter') handleAdd(); if (e.key === 'Escape') setIsAdding(false) }}
              />
              <button
                onClick={() => setNewImmediate(v => !v)}
                className={`text-[10px] px-1 rounded ${newImmediate ? 'text-green-400' : 'text-yellow-400'}`}
                title={newImmediate ? '즉시 전송' : '입력란에 채움'}
              >
                {newImmediate ? '전송' : '채움'}
              </button>
              <button
                onClick={handleAdd}
                disabled={saving || !newLabel.trim() || !newCommand.trim()}
                className="p-0.5 rounded-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 text-white"
              >
                <Check size={10} />
              </button>
              <button onClick={() => setIsAdding(false)} className="p-0.5 rounded-full text-[#555] hover:text-[#aaa]">
                <X size={10} />
              </button>
            </div>
          )}

          {/* 액션이 없고 추가 폼도 닫혀 있을 때 안내 */}
          {actions.length === 0 && !isAdding && !editMode && (
            <button
              onClick={() => { setEditMode(true); setIsAdding(true) }}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-[#1e1e1e] border border-dashed
                border-[#333] text-[#555] hover:text-indigo-400 hover:border-indigo-500 transition-colors text-xs shrink-0"
            >
              <Plus size={11} /> 퀵 액션 추가
            </button>
          )}
        </div>

        {/* 오른쪽 스크롤 */}
        <button onClick={() => scroll('right')}
          className="shrink-0 p-0.5 rounded text-[#444] hover:text-[#aaa] transition-colors">
          <ChevronRight size={13} />
        </button>

        {/* 편집 모드 + 추가 버튼 그룹 */}
        {editMode ? (
          <div className="flex items-center gap-1 shrink-0">
            {/* + 추가 버튼 (편집 모드에서만 표시) */}
            <button
              onClick={() => setIsAdding(v => !v)}
              title="퀵 액션 추가"
              className={`p-1 rounded transition-colors ${isAdding ? 'text-indigo-400' : 'text-[#555] hover:text-indigo-400'}`}
            >
              <Plus size={13} />
            </button>
            {/* 편집 모드 종료 */}
            <button
              onClick={exitEdit}
              title="편집 완료"
              className="p-1 rounded text-green-400 hover:text-green-300 transition-colors"
            >
              <Check size={13} />
            </button>
          </div>
        ) : (
          /* 편집 모드 진입 버튼 */
          <button
            onClick={() => setEditMode(true)}
            title="편집"
            className="shrink-0 p-1 rounded text-[#444] hover:text-[#aaa] transition-colors"
          >
            <Pencil size={12} />
          </button>
        )}
      </div>
    </div>
  )
}
