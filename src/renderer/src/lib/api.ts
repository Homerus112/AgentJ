const BASE = 'http://127.0.0.1:8765'
const WS   = 'ws://127.0.0.1:8765'

export async function checkHealth(): Promise<boolean> {
  try { const r = await fetch(`${BASE}/health`); return r.ok } catch { return false }
}

export async function sendChat(message: string): Promise<{ response: string; agent: string }> {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error(`API 오류: ${r.status}`)
  return r.json()
}

export async function getMemory() {
  const r = await fetch(`${BASE}/memory`)
  if (!r.ok) throw new Error('메모리 조회 실패')
  return r.json()
}

export async function getStats() {
  const r = await fetch(`${BASE}/stats`)
  if (!r.ok) throw new Error('통계 조회 실패')
  return r.json()
}

export async function getCareer() {
  const r = await fetch(`${BASE}/career`)
  if (!r.ok) throw new Error('커리어 조회 실패')
  return r.json()
}

export async function getTasks() {
  const r = await fetch(`${BASE}/tasks`)
  if (!r.ok) throw new Error('태스크 조회 실패')
  return r.json()
}

export async function rememberNote(note: string) {
  const r = await fetch(`${BASE}/memory/remember`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note }),
  })
  if (!r.ok) throw new Error('메모 저장 실패')
  return r.json()
}

export interface QuickAction {
  id: string; label: string; icon: string; command: string; send_immediately: boolean
}

export async function getQuickActions(): Promise<QuickAction[]> {
  const r = await fetch(`${BASE}/quick-actions`)
  if (!r.ok) throw new Error('퀵 액션 조회 실패')
  return r.json()
}

export async function addQuickAction(data: Omit<QuickAction, 'id'>): Promise<QuickAction> {
  const r = await fetch(`${BASE}/quick-actions`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('퀵 액션 추가 실패')
  return r.json()
}

export async function deleteQuickAction(id: string): Promise<void> {
  const r = await fetch(`${BASE}/quick-actions/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('퀵 액션 삭제 실패')
}

export async function reorderQuickActions(ids: string[]): Promise<QuickAction[]> {
  const r = await fetch(`${BASE}/quick-actions/reorder`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ids),
  })
  if (!r.ok) throw new Error('순서 변경 실패')
  return r.json()
}

export type WsMessage =
  | { type: 'thinking'; message: string; timestamp: string }
  | { type: 'response'; content: string; agent: string; timestamp: string }
  | { type: 'error';    message: string }

// WS keepalive: 20초마다 ping 전송
const WS_PING_INTERVAL = 20_000

export function createChatWebSocket(
  onMessage: (msg: WsMessage) => void,
  onOpen?:   () => void,
  onClose?:  () => void,
) {
  const socket = new WebSocket(`${WS}/ws/chat`)
  let pingTimer: ReturnType<typeof setInterval> | null = null

  socket.onopen = () => {
    // keepalive ping 시작
    pingTimer = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }))
      }
    }, WS_PING_INTERVAL)
    onOpen?.()
  }
  socket.onclose = () => {
    if (pingTimer) clearInterval(pingTimer)
    onClose?.()
  }
  socket.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data)
      if (parsed.type === 'pong') return  // keepalive 응답 무시
      onMessage(parsed as WsMessage)
    }
    catch { console.error('[WS] 파싱 오류:', e.data) }
  }
  return {
    send: (message: string) => socket.send(JSON.stringify({ message })),
    /** 서버에 취소 신호 전송 */
    sendCancel: () => {
      if (socket.readyState === WebSocket.OPEN)
        socket.send(JSON.stringify({ type: 'cancel' }))
    },
    close: () => { if (pingTimer) clearInterval(pingTimer); socket.close() },
    get readyState() { return socket.readyState },
  }
}

// ── 파일 업로드 ────────────────────────────────────────────────────────────────
export async function uploadFile(file: File): Promise<{ filename: string; content: string; chars: number }> {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!r.ok) throw new Error('파일 업로드 실패')
  return r.json()
}

// ── 브리핑 ─────────────────────────────────────────────────────────────────────
export async function getBriefing(refresh = false): Promise<{ date: string; briefing: string; generated_at: string }> {
  const r = await fetch(`${BASE}/briefing?refresh=${refresh}`)
  if (!r.ok) throw new Error('브리핑 조회 실패')
  return r.json()
}

// ── 포트폴리오 생성 ────────────────────────────────────────────────────────────
export interface PortfolioRequest {
  project_name: string; description: string; tech_stack: string
  duration?: string; impact?: string; github_url?: string
}
export async function generatePortfolio(data: PortfolioRequest): Promise<{ result: string; project: string }> {
  const r = await fetch(`${BASE}/portfolio/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!r.ok) throw new Error('포트폴리오 생성 실패')
  return r.json()
}

// ── 면접 코치 ──────────────────────────────────────────────────────────────────
export async function interviewChat(
  message: string,
  history: { role: string; content: string }[]
): Promise<{ response: string; agent: string }> {
  const r = await fetch(`${BASE}/interview/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
  if (!r.ok) throw new Error('면접 코치 오류')
  return r.json()
}

// ── 목표 드리프트 ──────────────────────────────────────────────────────────────
export async function getGoalStatus(): Promise<{
  status: string; total_goals: number; alerts: { goal: string; message: string; severity: string }[]
  alert_count: number
}> {
  const r = await fetch(`${BASE}/goal-status`)
  if (!r.ok) throw new Error('목표 상태 조회 실패')
  return r.json()
}

// ── Notion 푸시 ────────────────────────────────────────────────────────────────
export async function notionPush(title: string, content: string, category = 'memo'): Promise<{ success: boolean; url: string }> {
  const r = await fetch(`${BASE}/notion/push`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content, category }),
  })
  if (!r.ok) throw new Error('Notion 저장 실패')
  return r.json()
}

export async function getSchedule(): Promise<{ events: any[] }> {
  const r = await fetch(`${BASE}/schedule`)
  if (!r.ok) throw new Error('일정 조회 실패')
  return r.json()
}
