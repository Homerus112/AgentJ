import { create } from 'zustand'

export interface Message {
  id:        string
  role:      'user' | 'assistant' | 'thinking'
  content:   string
  agent?:    string
  timestamp: string
}

interface ChatStore {
  messages:     Message[]
  isLoading:    boolean
  isCancelled:  boolean          // 취소 플래그: 다음 응답 무시용
  apiStatus:    'ok' | 'error' | 'unknown'
  addMessage:   (msg: Message) => void
  setLoading:   (v: boolean) => void
  setApiStatus: (s: 'ok' | 'error' | 'unknown') => void
  clearMessages:() => void
  cancelLoading:() => void       // 로딩 즉시 취소
  resetCancelled:() => void      // 취소 플래그 리셋
  /** messageId 이후 메시지를 모두 제거하고 해당 메시지도 제거 (편집 재전송용) */
  truncateFrom: (messageId: string) => Message | null
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages:      [],
  isLoading:     false,
  isCancelled:   false,
  apiStatus:     'unknown',
  addMessage:    (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setLoading:    (v)   => set({ isLoading: v }),
  setApiStatus:  (s)   => set({ apiStatus: s }),
  clearMessages: ()    => set({ messages: [] }),
  cancelLoading: ()    => set({ isLoading: false, isCancelled: true,
    messages: get().messages.filter(m => m.id !== 'thinking') }),
  resetCancelled:()    => set({ isCancelled: false }),
  truncateFrom:  (id)  => {
    const msgs = get().messages
    const idx  = msgs.findIndex(m => m.id === id)
    if (idx === -1) return null
    const target = msgs[idx]
    set({ messages: msgs.slice(0, idx) })
    return target
  },
}))
