import { MessageSquare, BarChart2, Briefcase, Megaphone, Calendar, Mic, Package } from 'lucide-react'
import { useChatStore } from '@/store/chat'
import type { PageId } from '@/App'

const NAV_ITEMS: { icon: typeof MessageSquare; label: string; id: PageId }[] = [
  { icon: MessageSquare, label: '채팅',     id: 'chat'      },
  { icon: BarChart2,     label: '대시보드', id: 'dashboard' },
  { icon: Briefcase,     label: '커리어',   id: 'career'    },
  { icon: Megaphone,     label: '브랜드',   id: 'brand'     },
  { icon: Calendar,      label: '플래너',   id: 'planner'   },
  { icon: Mic,           label: '면접',     id: 'interview' },
  { icon: Package,       label: '포트폴리오', id: 'portfolio' },
]

interface Props { currentPage: PageId; onNavigate: (p: PageId) => void }

export default function Sidebar({ currentPage, onNavigate }: Props) {
  const apiStatus = useChatStore((s) => s.apiStatus)

  return (
    <div className="w-20 flex flex-col items-center bg-[#0a0a0a] border-r border-[#1e1e1e] py-3 gap-0.5 overflow-y-auto">
      {/* 로고 */}
      <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center mb-2 shrink-0">
        <span className="text-base font-bold text-indigo-400">J</span>
      </div>

      {NAV_ITEMS.map(({ icon: Icon, label, id }) => (
        <button key={id} onClick={() => onNavigate(id)}
          title={label}
          className={`w-16 h-[52px] flex flex-col items-center justify-center rounded-xl transition-all gap-0.5 shrink-0
            ${currentPage === id
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
              : 'text-[#666] hover:text-[#ccc] hover:bg-[#1a1a1a]'}`}>
          <Icon size={18} />
          <span className="text-[9px] font-medium leading-none">{label}</span>
        </button>
      ))}

      {/* 하단 상태 표시 */}
      <div className="mt-auto pt-3 shrink-0">
        <div className={`w-2 h-2 rounded-full mx-auto ${apiStatus === 'ok' ? 'bg-green-500' : apiStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'}`} />
        <p className="text-[8px] text-[#444] text-center mt-1">
          {apiStatus === 'ok' ? '온라인' : apiStatus === 'error' ? '오프라인' : '확인중'}
        </p>
      </div>
    </div>
  )
}
