import { useState } from 'react'
import { Loader2, CloudUpload, Copy, ChevronDown, ChevronUp } from 'lucide-react'
import { generatePortfolio, notionPush } from '@/lib/api'

type Section = 'readme' | 'linkedin' | 'resume' | 'interview'

function parseResult(text: string): Record<Section, string> {
  const sections: Record<Section, string> = { readme: '', linkedin: '', resume: '', interview: '' }
  const readmeMatch    = text.match(/###\s*README\s*###([\s\S]*?)(?=###\s*(LINKEDIN|RESUME_BULLET|INTERVIEW_SCRIPT)\s*###|$)/i)
  const linkedinMatch  = text.match(/###\s*LINKEDIN\s*###([\s\S]*?)(?=###\s*(README|RESUME_BULLET|INTERVIEW_SCRIPT)\s*###|$)/i)
  const resumeMatch    = text.match(/###\s*RESUME_BULLET\s*###([\s\S]*?)(?=###\s*(README|LINKEDIN|INTERVIEW_SCRIPT)\s*###|$)/i)
  const interviewMatch = text.match(/###\s*INTERVIEW_SCRIPT\s*###([\s\S]*?)(?=###\s*(README|LINKEDIN|RESUME_BULLET)\s*###|$)/i)
  if (readmeMatch)    sections.readme    = readmeMatch[1].trim()
  if (linkedinMatch)  sections.linkedin  = linkedinMatch[1].trim()
  if (resumeMatch)    sections.resume    = resumeMatch[1].trim()
  if (interviewMatch) sections.interview = interviewMatch[1].trim()
  return sections
}

interface OutputSectionProps {
  title: string; emoji: string; content: string; notionCategory?: string; notionTitle?: string
}

function OutputSection({ title, emoji, content, notionCategory = 'memo', notionTitle }: OutputSectionProps) {
  const [open,    setOpen]    = useState(true)
  const [saving,  setSaving]  = useState(false)
  const [copied,  setCopied]  = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500)
    })
  }

  const saveNotion = async () => {
    setSaving(true)
    try {
      await notionPush(notionTitle || title, content, notionCategory)
      alert('Notion에 저장됐습니다!')
    } catch { alert('Notion 저장 실패') }
    finally { setSaving(false) }
  }

  return (
    <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl overflow-hidden mb-3">
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-[#242424] transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-2">
          <span>{emoji}</span>
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
          <button
            onClick={copy}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-[#242424] hover:bg-[#2e2e2e] text-[#666] hover:text-white border border-[#333] transition-colors"
          >
            <Copy size={9} /> {copied ? '복사됨!' : '복사'}
          </button>
          <button
            onClick={saveNotion}
            disabled={saving}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-[#242424] hover:bg-[#2e2e2e] text-[#666] hover:text-indigo-400 border border-[#333] transition-colors disabled:opacity-40"
          >
            <CloudUpload size={9} /> {saving ? '저장 중...' : 'Notion'}
          </button>
          {open ? <ChevronUp size={13} className="text-[#555]" /> : <ChevronDown size={13} className="text-[#555]" />}
        </div>
      </div>
      {open && content && (
        <div className="px-4 pb-4">
          <pre className="text-xs text-[#ccc] whitespace-pre-wrap font-sans leading-relaxed border-t border-[#242424] pt-3">{content}</pre>
        </div>
      )}
    </div>
  )
}

export default function PortfolioPage() {
  const [form, setForm] = useState({
    project_name: '', description: '', tech_stack: '',
    duration: '', impact: '', github_url: '',
  })
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState<Record<Section, string> | null>(null)
  const [rawResult, setRawResult] = useState('')

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const generate = async () => {
    if (!form.project_name || !form.description || !form.tech_stack) return
    setLoading(true)
    setResult(null)
    try {
      const r = await generatePortfolio(form)
      setRawResult(r.result)
      setResult(parseResult(r.result))
    } catch { alert('포트폴리오 생성 오류. 서버를 확인해주세요.') }
    finally { setLoading(false) }
  }

  const saveAllToNotion = async () => {
    if (!result) return
    const full = Object.values(result).join('\n\n---\n\n')
    try {
      await notionPush(`포트폴리오: ${form.project_name}`, full, 'resume')
      alert('전체 Notion 저장 완료!')
    } catch { alert('Notion 저장 실패') }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-white">📦 포트폴리오 빌더</h2>
        {result && (
          <button
            onClick={saveAllToNotion}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 text-xs transition-colors"
          >
            <CloudUpload size={12} /> 전체 Notion 저장
          </button>
        )}
      </div>
      <p className="text-xs text-[#555] mb-6">프로젝트 정보 입력 → 버튼 한 번 → README + LinkedIn + 이력서 불릿 + 면접 스크립트 자동 생성</p>

      {/* 입력 폼 */}
      <div className="bg-[#1a1a1a] border border-[#2e2e2e] rounded-xl p-5 mb-5">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">프로젝트명 *</label>
            <input value={form.project_name} onChange={update('project_name')}
              placeholder="예: Agent J"
              className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors" />
          </div>
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">기술 스택 *</label>
            <input value={form.tech_stack} onChange={update('tech_stack')}
              placeholder="예: Python, FastAPI, React, TypeScript"
              className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors" />
          </div>
        </div>

        <div className="mb-4">
          <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">프로젝트 설명 *</label>
          <textarea value={form.description} onChange={update('description')}
            placeholder="어떤 문제를 해결했는지, 주요 기능은 무엇인지, 본인의 역할은 무엇인지 자세히 설명해주세요"
            rows={3}
            className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors resize-none" />
        </div>

        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">기간</label>
            <input value={form.duration} onChange={update('duration')}
              placeholder="예: 2개월 (2024.01~02)"
              className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors" />
          </div>
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">성과 / 임팩트</label>
            <input value={form.impact} onChange={update('impact')}
              placeholder="예: API 응답속도 40% 개선"
              className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors" />
          </div>
          <div>
            <label className="text-[10px] text-[#666] uppercase tracking-wide mb-1 block">GitHub URL</label>
            <input value={form.github_url} onChange={update('github_url')}
              placeholder="https://github.com/..."
              className="w-full bg-[#111] border border-[#2e2e2e] rounded-lg px-3 py-2 text-sm text-white placeholder-[#444] outline-none focus:border-indigo-500 transition-colors" />
          </div>
        </div>

        <button
          onClick={generate}
          disabled={loading || !form.project_name || !form.description || !form.tech_stack}
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <><Loader2 size={15} className="animate-spin" /> 포트폴리오 자산 생성 중...</>
          ) : '✨ 포트폴리오 자산 생성하기'}
        </button>
      </div>

      {/* 결과 출력 */}
      {result && (
        <div>
          <p className="text-xs text-[#555] mb-3">각 섹션을 클릭해 펼치거나 접을 수 있습니다. 복사 또는 Notion 저장 가능.</p>
          {result.readme    && <OutputSection title="README.md"     emoji="📋" content={result.readme}    notionCategory="research" notionTitle={`README: ${form.project_name}`} />}
          {result.linkedin  && <OutputSection title="LinkedIn 포스트"  emoji="💼" content={result.linkedin}  notionCategory="memo"     notionTitle={`LinkedIn: ${form.project_name}`} />}
          {result.resume    && <OutputSection title="이력서 불릿"   emoji="📄" content={result.resume}    notionCategory="resume"   notionTitle={`이력서: ${form.project_name}`} />}
          {result.interview && <OutputSection title="면접 스크립트" emoji="🎤" content={result.interview} notionCategory="memo"     notionTitle={`면접스크립트: ${form.project_name}`} />}
        </div>
      )}
    </div>
  )
}
