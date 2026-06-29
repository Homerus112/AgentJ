import { useEffect, useRef, useCallback, useState } from 'react'
import { useChatStore } from '@/store/chat'
import MessageBubble from './MessageBubble'
import InputBar from './InputBar'
import { createChatWebSocket } from '@/lib/api'
import type { WsMessage } from '@/lib/api'

let wsRef: ReturnType<typeof createChatWebSocket> | null = null

export default function ChatWindow() {
  const {
    messages, isLoading, apiStatus,
    addMessage, setLoading, clearMessages,
    cancelLoading, resetCancelled, truncateFrom,
  } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [editText, setEditText] = useState('')
  const [editKey,  setEditKey]  = useState(0)   // 같은 텍스트 재편집 감지용

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const connect = useCallback(() => {
    if (wsRef) return
    wsRef = createChatWebSocket(
      (msg: WsMessage) => {
        // 취소된 경우 응답 무시 후 플래그 리셋
        if (useChatStore.getState().isCancelled) {
          resetCancelled()
          return
        }
        if (msg.type === 'thinking') {
          addMessage({ id: 'thinking', role: 'thinking', content: msg.message, timestamp: msg.timestamp })
        } else if (msg.type === 'response') {
          useChatStore.setState((s) => ({
            messages: s.messages.filter(m => m.id !== 'thinking').concat({
              id: Date.now().toString(), role: 'assistant',
              content: msg.content, agent: msg.agent, timestamp: msg.timestamp,
            })
          }))
          setLoading(false)
        } else if (msg.type === 'error') {
          addMessage({ id: Date.now().toString(), role: 'assistant', content: `오류: ${msg.message}`, timestamp: new Date().toISOString() })
          setLoading(false)
        }
      },
      () => console.log('[WS] 연결됨'),
      () => { wsRef = null; setTimeout(connect, 1000) }  // 3s → 1s 재연결
    )
  }, [addMessage, setLoading, resetCancelled])

  useEffect(() => {
    if (apiStatus === 'ok') connect()
    return () => {}
  }, [apiStatus, connect])

  /** 일반 전송 */
  const handleSend = useCallback((text: string) => {
    if (!text.trim() || isLoading) return
    addMessage({ id: Date.now().toString(), role: 'user', content: text, timestamp: new Date().toISOString() })
    setLoading(true)
    if (wsRef?.readyState === WebSocket.OPEN) {
      wsRef.send(text)
    } else {
      setLoading(false)
      addMessage({ id: Date.now().toString(), role: 'assistant', content: '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.', timestamp: new Date().toISOString() })
    }
  }, [isLoading, addMessage, setLoading])

  /** 메시지 편집: store에서 해당 메시지 이후 제거 후 InputBar에 원문 주입 */
  const handleEditMessage = useCallback((messageId: string) => {
    const original = truncateFrom(messageId)
    if (original?.content) {
      setEditText(original.content)
      setEditKey(k => k + 1)
    }
  }, [truncateFrom])

  /** 취소: UI 즉시 복원 + 서버에 cancel 신호 */
  const handleCancel = useCallback(() => {
    cancelLoading()
    wsRef?.sendCancel()
  }, [cancelLoading])


  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
        <h1 className="text-sm font-medium text-[#888]">Agent J</h1>
        <button onClick={clearMessages} className="text-[10px] text-[#444] hover:text-[#888] transition-colors">초기화</button>
      </div>
      <div className="flex-1 overflow-y-auto py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <span className="text-3xl font-bold text-indigo-400">J</span>
            </div>
            <p className="text-[#555] text-sm">안녕하세요, Jeremy.<br />무엇을 도와드릴까요?</p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} onEdit={handleEditMessage} />
        ))}
        <div ref={bottomRef} />
      </div>
      <InputBar onSend={handleSend} onCancel={handleCancel} isLoading={isLoading} editText={editText} editKey={editKey} />
    </div>
  )
}
