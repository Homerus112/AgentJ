import { useState, useRef } from 'react'
import { Linkedin, Instagram, Sparkles, Copy, Check, RefreshCw, Send, ChevronDown, ChevronUp } from 'lucide-react'
import { sendChat } from '@/lib/api'

type Platform = 'linkedin' | 'instagram' | 'both'

// ── 플랫폼 자동 감지 ─────────────────────────────────────────────────────────
const LI_KEYWORDS  = ['linkedin', '링크드인', 'linkedin만', 'linkedin 포스트', '링크드인만', '링크드인 포스트']
const IG_KEYWORDS  = ['instagram', '인스타', '인스타그램', 'ig 포스트', '인스타만', '인스타그램만']

function detectPlatform(text: string): Platform {
  const t = text.toLowerCase()
  const hasLi = LI_KEYWORDS.some(k => t.includes(k))
  const hasIg  = IG_KEYWORDS.some(k => t.includes(k))
  if (hasLi && !hasIg) return 'linkedin'
  if (hasIg && !hasLi) return 'instagram'
  return 'both'
}

// ── Brand Agent 응답 파싱 ─────────────────────────────────────────────────────
function parseBrandResponse(text: string): { linkedin: string; instagram: string } {
  const liMatch = text.match(/###\s*LINKEDIN\s*###([\s\S]*?)(?=###\s*INSTAGRAM\s*###|$)/i)
  const igMatch = text.match(/###\s*INSTAGRAM\s*###([\s\S]*?)(?=###\s*LINKEDIN\s*###|$)/i)
  if (liMatch || igMatch) {
    return {
      linkedin:  liMatch ? liMatch[1].trim() : '',
      instagram: igMatch ? igMatch[1].trim() : '',
    }
  }
  // fallback: 키워드 기반
  const liKw = text.match(/linkedin[^\n]*\n([\s\S]*?)(?=instagram|$)/i)
  const igKw = text.match(/instagram[^\n]*\n([\s\S]*?)$/i)
  return {
    linkedin:  liKw ? liKw[1].trim() : text,
    instagram: igKw ? igKw[1].trim() : '',
  }
}

// ── DraftCard ──────────────────────────────────────────────────────────────────
function DraftCard({ platform, content }: { platform: 'linkedin' | 'instagram'; content: string }) {
  const [copied, setCopied] = useState(false)
  const isLi = platform === 'linkedin'

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex flex-col bg-[#141414] border rounded-2xl overflow-hidden
      ${isLi ? 'border-blue-500/25' : 'border-pink-500/25'}`}>
      {/* 헤더 */}
      <div className={`flex items-center justify-between px-4 py-2.5 border-b
        ${isLi ? 'border-blue-500/15 bg-blue-500/5' : 'border-pink-500/15 bg-pink-500/5'}`}>
        <div className="flex items-center gap-2">
          {isLi
            ? <Linkedin size={15} className="text-blue-400" />
            : <Instagram size={15} className="text-pink-400" />}
          <span className={`text-sm font-semibold ${isLi ? 'text-blue-300' : 'text-pink-300'}`}>
            {isLi ? 'LinkedIn' : 'Instagram'}
          </span>
          <span className="text-[10px] text-[#555] bg-[#1e1e1e] px-1.5 py-0.5 rounded">초안</span>
        </div>
        <button onClick={handleCopy}
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg transition-colors
            ${copied
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-[#1e1e1e] text-[#777] hover:text-[#ccc] border border-[#2a2a2a]'}`}>
          {copied ? <><Check size={11} />복사됨</> : <><Copy size={11} />복사</>}
        </button>
      </div>
      {/* 본문 */}
      <div className="flex-1 p-4 max-h-64 overflow-y-auto">
        {content
          ? <p className="text-sm text-[#d0d0d0] whitespace-pre-wrap leading-relaxed">{content}</p>
          : <p className="text-sm text-[#444] italic">내용 없음</p>}
      </div>
      {/* 글자 수 */}
      {content && (
        <div className={`px-4 py-1.5 border-t text-[10px] text-right text-[#555]
          ${isLi ? 'border-blue-500/10' : 'border-pink-500/10'}`}>
          {content.length.toLocaleString()}자
        </div>
      )}
    </div>
  )
}

// ── RevisionItem (히스토리) ───────────────────────────────────────────────────
interface RevisionEntry {
  id: number
  request: string
  linkedin: string
  instagram: string
  platform: Platform
}

// ── EXAMPLE TOPICS ────────────────────────────────────────────────────────────
const EXAMPLE_TOPICS = [
  '오늘 ML 프로젝트에서 배운 것들',
  'AI 에이전트 개발 1주일 회고',
  '취업 준비 중 깨달은 인사이트',
  '인스타 — Python 비동기 공부 후기',
  'LinkedIn — 데이터사이언스 커리어 팁',
]

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────
export default function BrandCenter() {
  const [topic,     setTopic]     = useState('')
  const [drafts,    setDrafts]    = useState<{ linkedin: string; instagram: string } | null>(null)
  const [platform,  setPlatform]  = useState<Platform>('both')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')

  // Revision 세션
  const [revisions,   setRevisions]   = useState<RevisionEntry[]>([])
  const [revInput,    setRevInput]    = useState('')
  const [revLoading,  setRevLoading]  = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const revInputRef = useRef<HTMLInputElement>(null)
  const revIdRef    = useRef(0)

  // 플랫폼 배지
  const platformBadge: Record<Platform, { label: string; color: string }> = {
    both:      { label: '전체',      color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
    linkedin:  { label: 'LinkedIn', color: 'text-blue-400  bg-blue-500/10  border-blue-500/20'  },
    instagram: { label: 'Instagram',color: 'text-pink-400  bg-pink-500/10  border-pink-500/20'  },
  }

  async function generate(overrideTopic?: string) {
    const t = (overrideTopic ?? topic).trim()
    if (!t || loading) return

    const detected = detectPlatform(t)
    setPlatform(detected)
    setLoading(true); setError(''); setDrafts(null); setRevisions([])

    const tag = detected !== 'both' ? ` [PLATFORM:${detected}]` : ''
    try {
      const r   = await sendChat(`/brand ${t}${tag}`)
      const parsed = parseBrandResponse(r.response)
      setDrafts(parsed)
    } catch {
      setError('생성 실패: 서버에 연결할 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function revise() {
    const req = revInput.trim()
    if (!req || revLoading || !drafts) return
    setRevLoading(true)

    // 이전 초안을 컨텍스트로 포함해서 revision 요청
    const context = [
      drafts.linkedin  ? `[현재 LinkedIn 초안]\n${drafts.linkedin}`  : '',
      drafts.instagram ? `[현재 Instagram 초안]\n${drafts.instagram}` : '',
    ].filter(Boolean).join('\n\n')

    const tag = platform !== 'both' ? ` [PLATFORM:${platform}]` : ''
    const msg = `/brand [REVISION REQUEST] ${req}${tag}\n\n${context}`

    try {
      const r = await sendChat(msg)
      const parsed = parseBrandResponse(r.response)

      const entry: RevisionEntry = {
        id:        ++revIdRef.current,
        request:   req,
        linkedin:  parsed.linkedin,
        instagram: parsed.instagram,
        platform,
      }
      setRevisions(prev => [entry, ...prev])
      setDrafts(parsed)
      setRevInput('')
    } catch {
      setError('수정 실패: 서버 오류')
    } finally {
      setRevLoading(false)
    }
  }

  // 현재 보여줄 플랫폼 카드 결정
  const showLi = drafts && (platform === 'both' || platform === 'linkedin') && drafts.linkedin
  const showIg = drafts && (platform === 'both' || platform === 'instagram') && drafts.instagram

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#0f0f0f]">

      {/* ── 헤더 ── */}
      <div className="mb-5">
        <h2 className="text-xl font-bold text-white mb-1">브랜드 센터</h2>
        <p className="text-sm text-[#666]">
          주제 입력 → LinkedIn + Instagram 초안 자동 생성 &nbsp;·&nbsp;
          <span className="text-[#444]">특정 플랫폼 이름 언급 시 해당 플랫폼만 생성</span>
        </p>
      </div>

      {/* ── 입력 영역 ── */}
      <div className="bg-[#141414] border border-[#252525] rounded-2xl p-5 mb-5">
        <label className="block text-xs font-medium text-[#888] mb-2 uppercase tracking-wider">
          주제 / 경험 / 인사이트
        </label>
        <textarea
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); generate() } }}
          placeholder="예: 오늘 ML 모델 튜닝하며 배운 것들 / 인스타 — 취업 준비 후기..."
          rows={2}
          className="w-full bg-[#0f0f0f] border border-[#2a2a2a] rounded-xl px-4 py-3 text-sm
            text-[#f0f0f0] placeholder-[#444] outline-none focus:border-indigo-500 transition-colors
            resize-none mb-3"
        />

        {/* 예시 주제 */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {EXAMPLE_TOPICS.map(ex => (
            <button key={ex} onClick={() => { setTopic(ex); generate(ex) }}
              className="text-[11px] text-[#666] bg-[#1a1a1a] hover:bg-[#222] border border-[#2a2a2a]
                hover:border-[#444] rounded-lg px-2.5 py-1 transition-colors hover:text-[#aaa]">
              {ex}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => generate()} disabled={!topic.trim() || loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500
              disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-medium
              text-white transition-colors shadow-lg shadow-indigo-600/20">
            {loading
              ? <><RefreshCw size={14} className="animate-spin" />생성 중...</>
              : <><Sparkles size={14} />초안 생성</>}
          </button>

          {/* 플랫폼 감지 배지 */}
          {topic.trim() && (() => {
            const det = detectPlatform(topic)
            const { label, color } = platformBadge[det]
            return (
              <span className={`text-[11px] px-2 py-1 rounded-lg border font-medium ${color}`}>
                {det === 'both' ? '🎯 두 플랫폼 생성' : `🎯 ${label}만 생성`}
              </span>
            )
          })()}

          {drafts && (
            <button onClick={() => { setDrafts(null); setTopic(''); setRevisions([]) }}
              className="text-sm text-[#666] hover:text-[#aaa] transition-colors ml-auto">
              초기화
            </button>
          )}
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            {error}
          </p>
        )}
      </div>

      {/* ── 로딩 상태 ── */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center">
            <Sparkles size={20} className="text-indigo-400 animate-pulse" />
          </div>
          <div className="text-center">
            <p className="text-sm text-[#888]">초안을 작성하고 있습니다...</p>
            <p className="text-xs text-[#555] mt-1">
              {platform === 'both' ? 'LinkedIn + Instagram' : platformBadge[platform].label} 생성 중
            </p>
          </div>
        </div>
      )}

      {/* ── 결과 카드 ── */}
      {drafts && !loading && (
        <>
          {/* 현재 플랫폼 배지 */}
          <div className="flex items-center gap-2 mb-4">
            <span className={`text-xs px-2.5 py-1 rounded-lg border font-medium ${platformBadge[platform].color}`}>
              {platformBadge[platform].label}
            </span>
            <span className="text-xs text-[#555]">
              {revisions.length > 0 && `수정 ${revisions.length}회`}
            </span>
          </div>

          {/* 카드 그리드: both면 2열, 단일 플랫폼이면 1열 */}
          <div className={`grid gap-4 mb-5 ${platform === 'both' ? 'grid-cols-2' : 'grid-cols-1 max-w-xl'}`}>
            {showLi && <DraftCard platform="linkedin"  content={drafts.linkedin}  />}
            {showIg && <DraftCard platform="instagram" content={drafts.instagram} />}
          </div>

          {/* ── Revision & Review 세션 ── */}
          <div className="bg-[#141414] border border-[#252525] rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-[#252525] flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Revision & Review</p>
                <p className="text-xs text-[#555] mt-0.5">수정 요청을 입력하면 초안을 업데이트합니다</p>
              </div>
              {revisions.length > 0 && (
                <button onClick={() => setShowHistory(v => !v)}
                  className="flex items-center gap-1 text-xs text-[#666] hover:text-[#aaa] transition-colors">
                  히스토리 {revisions.length}건
                  {showHistory ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
              )}
            </div>

            {/* 수정 입력 */}
            <div className="p-4">
              <div className="flex gap-2">
                <input
                  ref={revInputRef}
                  type="text"
                  value={revInput}
                  onChange={e => setRevInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') revise() }}
                  placeholder={
                    platform === 'linkedin'  ? 'LinkedIn 수정 요청... (예: 더 짧게, 영어로, 해시태그 추가)' :
                    platform === 'instagram' ? 'Instagram 수정 요청... (예: 이모지 더, 감성적으로)' :
                    '수정 요청 입력... (예: 두 플랫폼 모두 더 짧게, LinkedIn만 영어로)'
                  }
                  disabled={revLoading}
                  className="flex-1 bg-[#0f0f0f] border border-[#2a2a2a] rounded-xl px-3 py-2
                    text-sm text-[#f0f0f0] placeholder-[#444] outline-none
                    focus:border-indigo-500 transition-colors disabled:opacity-50"
                />
                <button onClick={revise} disabled={!revInput.trim() || revLoading}
                  className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500
                    disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm text-white
                    transition-colors shrink-0">
                  {revLoading
                    ? <RefreshCw size={13} className="animate-spin" />
                    : <Send size={13} />}
                  {revLoading ? '수정 중' : '수정'}
                </button>
              </div>

              {/* 빠른 수정 버튼 */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {[
                  '더 짧게', '더 길게', '영어로 변환', '해시태그 더 추가',
                  '더 전문적으로', '더 캐주얼하게', '이모지 추가',
                ].map(hint => (
                  <button key={hint}
                    onClick={() => { setRevInput(hint); setTimeout(() => revInputRef.current?.focus(), 50) }}
                    className="text-[10px] text-[#666] hover:text-[#aaa] bg-[#1a1a1a]
                      hover:bg-[#222] border border-[#2a2a2a] rounded-md px-2 py-0.5 transition-colors">
                    {hint}
                  </button>
                ))}
              </div>
            </div>

            {/* 수정 히스토리 */}
            {showHistory && revisions.length > 0 && (
              <div className="border-t border-[#252525] px-4 py-3 space-y-3 max-h-60 overflow-y-auto">
                {revisions.map((r, i) => (
                  <div key={r.id} className="text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-4 h-4 rounded-full bg-indigo-600/20 border border-indigo-500/30
                        text-indigo-400 flex items-center justify-center text-[9px] font-bold shrink-0">
                        {revisions.length - i}
                      </span>
                      <span className="text-[#999] font-medium">"{r.request}"</span>
                      <button onClick={() => setDrafts({ linkedin: r.linkedin, instagram: r.instagram })}
                        className="ml-auto text-[#555] hover:text-indigo-400 transition-colors text-[10px]">
                        복원
                      </button>
                    </div>
                    {r.linkedin && (
                      <p className="text-[#555] pl-6 truncate">
                        <span className="text-blue-500/60">LI:</span> {r.linkedin.slice(0, 60)}...
                      </p>
                    )}
                    {r.instagram && (
                      <p className="text-[#555] pl-6 truncate">
                        <span className="text-pink-500/60">IG:</span> {r.instagram.slice(0, 60)}...
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── 빈 상태 ── */}
      {!drafts && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/10 to-pink-500/10
            border border-white/5 flex items-center justify-center">
            <Sparkles size={24} className="text-indigo-400" />
          </div>
          <div>
            <p className="text-[#666] text-sm font-medium mb-1">아직 생성된 콘텐츠가 없어요</p>
            <p className="text-[#444] text-xs">
              위 입력창에 주제를 입력하거나 예시를 클릭하세요<br />
              <span className="text-[#333]">
                "인스타" 또는 "LinkedIn" 언급 시 해당 플랫폼만 생성
              </span>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
