import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts'
import { MessageSquare, Clock, StickyNote, TrendingUp, RefreshCw, CloudUpload, AlertTriangle, CheckCircle } from 'lucide-react'
import { getStats, getMemory, getBriefing, getGoalStatus, notionPush } from '@/lib/api'

const COLORS: Record<string, string> = {
  dev: '#4ade80', planner: '#60a5fa', writer: '#facc15', news: '#fb923c',
  career: '#f87171', brand: '#f472b6', research: '#c084fc', vision: '#22d3ee',
  general: '#818cf8', coach: '#fbbf24', knowledge: '#2dd4bf', interview: '#a78bfa',
  portfolio: '#34d399',
}

function KpiCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4 flex items-center gap-3">
      <div className="p-2 rounded-lg bg-[#242424] text-indigo-400">{icon}</div>
      <div>
        <p className="text-[11px] text-[#666] mb-0.5">{label}</p>
        <p className="text-lg font-semibold text-white">{value}</p>
        {sub && <p className="text-[10px] text-[#555]">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats,        setStats]        = useState<any>(null)
  const [memory,       setMemory]       = useState<any>(null)
  const [briefing,     setBriefing]     = useState<{ date: string; briefing: string; generated_at: string } | null>(null)
  const [goalStatus,   setGoalStatus]   = useState<any>(null)
  const [bLoading,     setBLoading]     = useState(false)
  const [notionSaving, setNotionSaving] = useState(false)

  useEffect(() => {
    getStats().then(setStats).catch(() => {})
    getMemory().then(setMemory).catch(() => {})
    getGoalStatus().then(setGoalStatus).catch(() => {})
    // 브리핑 로드 (캐시 우선)
    setBLoading(true)
    getBriefing(false).then(setBriefing).catch(() => {}).finally(() => setBLoading(false))
  }, [])

  const refreshBriefing = () => {
    setBLoading(true)
    getBriefing(true).then(setBriefing).catch(() => {}).finally(() => setBLoading(false))
  }

  const saveBriefingToNotion = async () => {
    if (!briefing) return
    setNotionSaving(true)
    try {
      await notionPush(`브리핑 ${briefing.date}`, briefing.briefing, 'memo')
      alert('Notion에 저장됐습니다!')
    } catch { alert('Notion 저장 실패. NOTION_API_KEY를 확인해주세요.') }
    finally { setNotionSaving(false) }
  }

  const barData = stats ? Object.entries(stats.agent_counts ?? {}).map(([name, count]) => ({ name, count })) : []
  const pieData = barData.map(d => ({ ...d, fill: COLORS[d.name] ?? '#555' }))
  const notes   = memory?.notes ?? []
  const alerts  = goalStatus?.alerts ?? []

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">
      <h2 className="text-lg font-semibold text-white mb-5">대시보드</h2>

      {/* 🌅 오늘의 브리핑 */}
      <div className="bg-[#1a1a1a] border border-indigo-500/30 rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🌅</span>
            <p className="text-sm font-medium text-white">오늘의 브리핑</p>
            {briefing && <span className="text-[10px] text-[#555]">{briefing.date}</span>}
          </div>
          <div className="flex items-center gap-1.5">
            {briefing && (
              <button
                onClick={saveBriefingToNotion}
                disabled={notionSaving}
                title="Notion에 저장"
                className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#242424] hover:bg-[#2e2e2e] text-[#666] hover:text-indigo-400 text-[10px] transition-colors disabled:opacity-40"
              >
                <CloudUpload size={11} />
                {notionSaving ? '저장 중...' : 'Notion'}
              </button>
            )}
            <button
              onClick={refreshBriefing}
              disabled={bLoading}
              title="브리핑 새로 생성"
              className="p-1.5 rounded-lg text-[#555] hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors disabled:opacity-40"
            >
              <RefreshCw size={13} className={bLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
        {bLoading ? (
          <div className="flex items-center gap-2 py-4">
            <RefreshCw size={14} className="text-indigo-400 animate-spin" />
            <p className="text-xs text-[#555]">브리핑 생성 중...</p>
          </div>
        ) : briefing ? (
          <div className="text-xs text-[#bbb] whitespace-pre-wrap leading-relaxed">{briefing.briefing}</div>
        ) : (
          <p className="text-xs text-[#444] py-2">서버 연결 후 브리핑이 자동 생성됩니다</p>
        )}
      </div>

      {/* 🎯 목표 드리프트 알림 */}
      {alerts.length > 0 && (
        <div className="bg-yellow-500/5 border border-yellow-500/30 rounded-xl p-4 mb-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={14} className="text-yellow-400" />
            <p className="text-sm font-medium text-yellow-300">목표 드리프트 감지</p>
          </div>
          <div className="space-y-2">
            {alerts.map((a: any, i: number) => (
              <div key={i} className="flex items-start gap-2 text-xs text-[#bbb]">
                <span className="text-yellow-400 mt-0.5">•</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {goalStatus && alerts.length === 0 && goalStatus.status === 'analyzed' && (
        <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-3 mb-5 flex items-center gap-2">
          <CheckCircle size={13} className="text-green-400 shrink-0" />
          <p className="text-xs text-[#888]">목표 {goalStatus.total_goals}개 — 드리프트 없음 ✅</p>
        </div>
      )}

      {/* KPI 카드 */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <KpiCard icon={<MessageSquare size={16} />} label="총 대화 수" value={String(stats?.total_conversations ?? 0)} />
        <KpiCard icon={<TrendingUp size={16} />}    label="활성 에이전트" value={String(barData.length)} sub="종류" />
        <KpiCard icon={<StickyNote size={16} />}    label="저장된 메모" value={String(notes.length)} />
        <KpiCard icon={<Clock size={16} />}          label="마지막 사용"
          value={stats?.last_used ? new Date(stats.last_used).toLocaleDateString('ko-KR') : '-'} />
      </div>

      {/* 차트 */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
          <p className="text-xs text-[#666] mb-3 font-medium">에이전트별 사용 횟수</p>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={barData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 10, fill: '#555' }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#666' }} width={60} />
                <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8, fontSize: 11 }} />
                <Bar dataKey="count" radius={[0,4,4,0]}>
                  {barData.map(e => <Cell key={e.name} fill={COLORS[e.name] ?? '#555'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-[#444] py-8 text-center">대화 기록 없음</p>}
        </div>

        <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
          <p className="text-xs text-[#666] mb-3 font-medium">에이전트 분포</p>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={pieData} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={60} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8, fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-[#444] py-8 text-center">데이터 없음</p>}
        </div>
      </div>

      {/* 최근 메모 */}
      <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-4">
        <p className="text-xs text-[#666] mb-3 font-medium">최근 메모</p>
        {notes.length > 0 ? (
          <div className="space-y-2">
            {notes.slice(0, 6).map((n: any, i: number) => (
              <div key={i} className="text-xs text-[#aaa] bg-[#111] border border-[#1e1e1e] rounded-lg px-3 py-2">
                {n.date && <span className="text-[#555] mr-1">[{n.date}]</span>}
                {n.note ?? n.content ?? String(n)}
              </div>
            ))}
          </div>
        ) : <p className="text-xs text-[#444]">저장된 메모 없음</p>}
      </div>
    </div>
  )
}
