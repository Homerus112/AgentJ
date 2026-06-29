import { Minus, Square, X } from 'lucide-react'
import agentJLogo from '@/assets/agent-j-logo.png'

export default function TitleBar() {
  return (
    <div className="flex items-center justify-between h-9 bg-[#0a0a0a] border-b border-[#1e1e1e] select-none" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}>
      <div className="flex items-center gap-2 px-4">
        <img src={agentJLogo} alt="J" className="w-5 h-5 object-contain" />
        <span className="text-[#444] text-xs">Agent J</span>
      </div>
      <div className="flex" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        {[
          { icon: <Minus size={12} />, action: () => window.electron.minimize(), hover: 'hover:bg-[#222]' },
          { icon: <Square size={10} />, action: () => window.electron.maximize(), hover: 'hover:bg-[#222]' },
          { icon: <X size={12} />, action: () => window.electron.close(), hover: 'hover:bg-red-600' },
        ].map((btn, i) => (
          <button key={i} onClick={btn.action}
            className={`w-10 h-9 flex items-center justify-center text-[#555] ${btn.hover} transition-colors`}>
            {btn.icon}
          </button>
        ))}
      </div>
    </div>
  )
}
