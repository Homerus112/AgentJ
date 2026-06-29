import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { getStats, getMemory } from '@/lib/api'

const COLORS: Record<string, string> = {
  dev: '#4ade80', planner: '#60a5fa', writer: '#facc15', news: '#fb923c',
  career: '#f87171', brand: '#f472b6', research: '#c084fc', vision: '#22d3ee',
  general: '#818cf8', coach: '#fbbf24', knowledge: '#2dd4bf',
}

export default function RightPanel() {
  const [stats,  setStats]  = useState<any>(null)
  const [memory, setMemory] = useState<any>(null)

  useEffect(() => {
    getStats().then(setStats).catch(() => {})
    getMemory().then(setMemory).catch(() => {})
  }, [])

  const chartData = stats ? Object.entries(stats.agent_counts ?? {}).map(([name, count]) => ({ name, count })) : []

  return (
    <div className="w-64 border-l border-[#1e1e1e] bg-[#0a0a0a] p-4 flex flex-col gap-5 overflow-y-auto">
      <div>
        <p className="text-xs text-[#666] mb-3 font-medium uppercase tracking-wider">에이전트 통계</p>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 8, top: 0, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#666' }} width={55} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8, fontSize: 11 }} />
              <Bar dataKey="count" radius={[0,4,4,0]}>
                {chartData.map((e) => <Cell key={e.name} fill={COLORS[e.name] ?? '#555'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : <p className="text-xs text-[#444]">데이터 없음</p>}
        {stats && (
          <div className="mt-2 flex gap-3 text-[10px] text-[#555]">
            <span>총 {stats.total_conversations ?? 0}회</span>
            {stats.last_used && <span>마지막: {new Date(stats.last_used).toLocaleDateString('ko-KR')}</span>}
          </div>
        )}
      </div>
      <div>
        <p className="text-xs text-[#666] mb-2 font-medium uppercase tracking-wider">메모리</p>
        {memory?.notes?.length > 0 ? (
          <div className="space-y-1.5">
            {memory.notes.slice(0, 5).map((n: any, i: number) => (
              <div key={i} className="text-[11px] text-[#888] bg-[#111] border border-[#1e1e1e] rounded-lg px-2.5 py-1.5 leading-snug">
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
