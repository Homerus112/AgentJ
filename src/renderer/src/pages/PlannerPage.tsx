import { useEffect, useState } from 'react'
import { CheckSquare, Clock, AlertCircle, RefreshCw, Calendar } from 'lucide-react'
import { getTasks, sendChat } from '@/lib/api'

const PRIORITY_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  high:   { label: 'High',   color: 'text-red-400 border-red-500/30',    icon: <AlertCircle size={12} className="text-red-400" /> },
  medium: { label: 'Medium', color: 'text-yellow-400 border-yellow-500/30', icon: <Clock size={12} className="text-yellow-400" /> },
  low:    { label: 'Low',    color: 'text-green-400 border-green-500/30', icon: <CheckSquare size={12} className="text-green-400" /> },
}

export default function PlannerPage() {
  const [tasks,   setTasks]   = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [aiReply, setAiReply] = useState('')
  const [aiLoad,  setAiLoad]  = useState(false)

  const loadTasks = () => {
    setLoading(true)
    getTasks().then(d => setTasks(d.tasks ?? [])).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { loadTasks() }, [])

  const askSchedule = async () => {
    setAiLoad(true)
    try { const r = await sendChat('/schedule'); setAiReply(r.response) }
    catch { setAiReply('서버 연결 오류') }
    finally { setAiLoad(false) }
  }

  const byPriority = ['high', 'medium', 'low'].reduce((acc, p) => {
    acc[p] = tasks.filter(t => t.priority === p); return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">플래너</h2>
        <div className="flex gap-2">
          <button onClick={askSchedule} disabled={aiLoad}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1a1a1a] border border-[#2e2e2e] hover:border-indigo-500 rounded-lg text-xs text-[#aaa] transition-colors">
            <Calendar size={12} className={aiLoad ? 'animate-spin' : ''} /> 일정 확인
          </button>
          <button onClick={loadTasks} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-xs text-white transition-colors">
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> 새로고침
          </button>
        </div>
      </div>

      {aiReply && (
        <div className="bg-[#1a1a1a] border border-indigo-500/30 rounded-xl p-4 mb-5 text-sm text-[#ccc] whitespace-pre-wrap">{aiReply}</div>
      )}

      {loading ? <p className="text-[#555] text-sm">로딩 중...</p> : tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <CheckSquare size={32} className="text-[#333]" />
          <p className="text-sm text-[#555]">할 일이 없습니다<br /><span className="text-xs">J에게 "할 일 추가해줘"라고 말해보세요</span></p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {['high', 'medium', 'low'].map(p => {
            const meta = PRIORITY_META[p]
            return (
              <div key={p} className={`bg-[#1a1a1a] border rounded-xl p-4 ${meta.color.split(' ')[1]}`}>
                <div className="flex items-center gap-1.5 mb-3">
                  {meta.icon}
                  <span className={`text-xs font-medium ${meta.color.split(' ')[0]}`}>{meta.label} ({byPriority[p].length})</span>
                </div>
                <div className="space-y-2 min-h-[80px]">
                  {byPriority[p].map((t: any, i: number) => (
                    <div key={i} className="bg-[#111] border border-[#1e1e1e] rounded-lg px-3 py-2">
                      <p className="text-xs text-[#ddd]">{t.title}</p>
                      {t.due_date && <p className="text-[10px] text-[#555] mt-0.5">{t.due_date}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
