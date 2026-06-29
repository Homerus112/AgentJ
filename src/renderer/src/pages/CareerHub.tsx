import { useEffect, useState } from 'react'
import { Target, Briefcase, BookOpen, RefreshCw, CloudUpload, Mail, AlertTriangle } from 'lucide-react'
import { getCareer, sendChat, notionPush } from '@/lib/api'

const STATUS_COLS = [
  { id: 'wishlist',  label: '관심',   color: 'border-gray-500'   },
  { id: 'applied',   label: '지원',   color: 'border-blue-500'   },
  { id: 'interview', label: '면접',   color: 'border-yellow-500' },
  { id: 'offer',     label: '오퍼',   color: 'border-green-500'  },
  { id: 'rejected',  label: '불합격', color: 'border-red-500'    },
]

function daysSince(dateStr?: string): number | null {
  if (!dateStr) return null
  try {
    const diff = Date.now() - new Date(dateStr).getTime()
    return Math.floor(diff / (1000 * 60 * 60 * 24))
  } catch { return null }
}

function DaysBadge({ days, status }: { days: number; status: string }) {
  const urgent = days >= 14 && status === 'applied'
  const warn   = days >= 7  && days < 14 && status === 'applied'
  const cls = urgent
    ? 'bg-red-500/20 text-red-300 border-red-500/40'
    : warn
    ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
    : 'bg-[#1e1e1e] text-[#666] border-[#2e2e2e]'
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${cls} font-mono`}>
      D+{days}
    </span>
  )
}

export default function CareerHub() {
  const [career,       setCareer]       = useState<any>({})
  const [loading,      setLoading]      = useState(true)
  const [aiSummary,    setAiSummary]    = useState('')
  const [aiLoading,    setAiLoading]    = useState(false)
  const [followupFor,  setFollowupFor]  = useState<string | null>(null)
  const [followupText, setFollowupText] = useState('')
  const [followupLoading, setFollowupLoading] = useState(false)
  const [notionSaving, setNotionSaving] = useState<string | null>(null)

  useEffect(() => {
    getCareer().then(setCareer).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const fetchAiSummary = async () => {
    setAiLoading(true)
    try { const r = await sendChat('/career'); setAiSummary(r.response) }
    catch { setAiSummary('서버 연결 오류') }
    finally { setAiLoading(false) }
  }

  const generateFollowup = async (app: any) => {
    setFollowupFor(app.company)
    setFollowupLoading(true)
    const days = daysSince(app.applied_date) ?? 0
    try {
      const r = await sendChat(
        `${app.company} ${app.role || ''} 포지션에 지원한 지 ${days}일이 됐어. ` +
        `채용담당자에게 보낼 정중한 follow-up 이메일 초안을 영어로 작성해줘. ` +
        `이름은 Jeremy, 포지션은 ${app.role || 'Software Engineer'}야.`
      )
      setFollowupText(r.response)
    } catch { setFollowupText('이메일 생성 오류') }
    finally { setFollowupLoading(false) }
  }

  const saveToNotion = async (app: any) => {
    if (!followupText || followupFor !== app.company) return
    setNotionSaving(app.company)
    try {
      await notionPush(`Follow-up: ${app.company} ${app.role || ''}`, followupText, 'memo')
      alert('Notion에 저장됐습니다!')
    } catch { alert('Notion 저장 실패') }
    finally { setNotionSaving(null) }
  }

  const goals        = career.goals        ?? []
  const applications = career.applications ?? []
  const skills       = career.skills       ?? []
  const byStatus     = STATUS_COLS.reduce((acc, col) => {
    acc[col.id] = applications.filter((a: any) => a.status === col.id); return acc
  }, {} as Record<string, any[]>)

  // follow-up 필요한 지원 목록 (D+14 이상)
  const needsFollowup = applications.filter((a: any) => {
    const d = daysSince(a.applied_date)
    return d !== null && d >= 14 && a.status === 'applied'
  })

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">커리어 허브</h2>
        <button onClick={fetchAiSummary} disabled={aiLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-xs text-white transition-colors">
          <RefreshCw size={12} className={aiLoading ? 'animate-spin' : ''} /> AI 요약
        </button>
      </div>

      {aiSummary && (
        <div className="bg-[#1a1a1a] border border-indigo-500/30 rounded-xl p-4 mb-5 text-sm text-[#ccc] whitespace-pre-wrap">{aiSummary}</div>
      )}

      {/* Follow-up 알림 배너 */}
      {needsFollowup.length > 0 && (
        <div className="bg-red-500/5 border border-red-500/30 rounded-xl p-3 mb-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={13} className="text-red-400" />
            <span className="text-xs font-medium text-red-300">Follow-up 시점 도달 ({needsFollowup.length}건)</span>
          </div>
          <div className="space-y-1.5">
            {needsFollowup.map((a: any, i: number) => {
              const days = daysSince(a.applied_date)!
              return (
                <div key={i} className="flex items-center justify-between gap-2">
                  <span className="text-xs text-[#bbb]">
                    {a.company} {a.role && <span className="text-[#555]">— {a.role}</span>}
                    <span className="ml-2 text-red-400 text-[10px]">D+{days}</span>
                  </span>
                  <button
                    onClick={() => generateFollowup(a)}
                    disabled={followupLoading && followupFor === a.company}
                    className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 text-[10px] border border-red-500/30 transition-colors disabled:opacity-50"
                  >
                    <Mail size={10} />
                    {followupLoading && followupFor === a.company ? '생성 중...' : 'Follow-up 초안'}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Follow-up 이메일 결과 */}
      {followupText && (
        <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4 mb-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-[#888]">✉️ Follow-up 이메일 초안 — {followupFor}</p>
            <div className="flex gap-1.5">
              <button
                onClick={() => { if (followupFor) saveToNotion({ company: followupFor, role: '' }) }}
                disabled={notionSaving === followupFor}
                className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-[#242424] hover:bg-[#2e2e2e] text-[#666] hover:text-indigo-400 transition-colors"
              >
                <CloudUpload size={9} /> Notion
              </button>
              <button onClick={() => { setFollowupText(''); setFollowupFor(null) }}
                className="text-[10px] text-[#555] hover:text-[#aaa] px-1">✕</button>
            </div>
          </div>
          <pre className="text-xs text-[#ccc] whitespace-pre-wrap font-sans leading-relaxed">{followupText}</pre>
        </div>
      )}

      {loading ? <p className="text-[#555] text-sm">로딩 중...</p> : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {/* 목표 */}
            <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3"><Target size={14} className="text-indigo-400" /><p className="text-xs font-medium text-[#888]">목표</p></div>
              {goals.length > 0 ? goals.map((g: any, i: number) => (
                <div key={i} className="mb-2">
                  <p className="text-xs text-white">{g.title}</p>
                  <div className="h-1 bg-[#2a2a2a] rounded-full mt-1"><div className="h-1 bg-indigo-500 rounded-full" style={{ width: `${g.progress ?? 0}%` }} /></div>
                  <p className="text-[10px] text-[#555] mt-0.5">{g.progress ?? 0}%</p>
                </div>
              )) : <p className="text-xs text-[#444]">목표 없음</p>}
            </div>

            {/* 스킬 */}
            <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3"><BookOpen size={14} className="text-green-400" /><p className="text-xs font-medium text-[#888]">스킬</p></div>
              {skills.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {skills.map((s: string, i: number) => (
                    <span key={i} className="px-2 py-0.5 bg-[#242424] border border-[#333] rounded-full text-[10px] text-[#aaa]">{s}</span>
                  ))}
                </div>
              ) : <p className="text-xs text-[#444]">스킬 없음</p>}
            </div>

            {/* 지원 요약 */}
            <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3"><Briefcase size={14} className="text-blue-400" /><p className="text-xs font-medium text-[#888]">지원 현황</p></div>
              <div className="space-y-1">
                {STATUS_COLS.map(col => (
                  <div key={col.id} className="flex justify-between text-xs">
                    <span className="text-[#666]">{col.label}</span>
                    <span className="text-white">{(byStatus[col.id] ?? []).length}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 지원 파이프라인 — D+N 배지 포함 */}
          <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
            <p className="text-xs font-medium text-[#888] mb-3">지원 파이프라인</p>
            <div className="grid grid-cols-5 gap-2">
              {STATUS_COLS.map(col => (
                <div key={col.id} className={`border-t-2 ${col.color} pt-2`}>
                  <p className="text-[10px] text-[#666] mb-2">{col.label} ({(byStatus[col.id] ?? []).length})</p>
                  <div className="space-y-1.5 min-h-[60px]">
                    {(byStatus[col.id] ?? []).map((a: any, i: number) => {
                      const days = daysSince(a.applied_date)
                      return (
                        <div key={i} className="bg-[#242424] rounded-lg px-2 py-1.5">
                          <p className="text-[10px] text-[#ccc] truncate">{a.company}</p>
                          {a.role && <p className="text-[9px] text-[#555] truncate">{a.role}</p>}
                          {days !== null && (
                            <div className="mt-1">
                              <DaysBadge days={days} status={a.status} />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
