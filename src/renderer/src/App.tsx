import { useEffect, useState } from 'react'
import TitleBar      from '@/components/TitleBar'
import Sidebar       from '@/components/Sidebar'
import ChatWindow    from '@/components/ChatWindow'
import RightPanel    from '@/components/RightPanel'
import Dashboard     from '@/pages/Dashboard'
import CareerHub     from '@/pages/CareerHub'
import BrandCenter   from '@/pages/BrandCenter'
import PlannerPage   from '@/pages/PlannerPage'
import InterviewPage from '@/pages/InterviewPage'
import PortfolioPage from '@/pages/PortfolioPage'
import { useChatStore } from '@/store/chat'
import { checkHealth } from '@/lib/api'

export type PageId = 'chat' | 'dashboard' | 'career' | 'brand' | 'planner' | 'interview' | 'portfolio'

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageId>('chat')
  const setApiStatus = useChatStore((s) => s.setApiStatus)

  useEffect(() => {
    const check = async () => { const ok = await checkHealth(); setApiStatus(ok ? 'ok' : 'error') }
    check()
    const id = setInterval(check, 10_000)
    return () => clearInterval(id)
  }, [setApiStatus])

  return (
    <div className="flex flex-col h-screen bg-[#0f0f0f] text-[#f5f5f5] overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
        {currentPage === 'chat'      && <><ChatWindow /><RightPanel /></>}
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'career'    && <CareerHub />}
        {currentPage === 'brand'     && <BrandCenter />}
        {currentPage === 'planner'   && <PlannerPage />}
        {currentPage === 'interview' && <InterviewPage />}
        {currentPage === 'portfolio' && <PortfolioPage />}
      </div>
    </div>
  )
}
