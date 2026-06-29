declare module '*.png' {
  const src: string
  export default src
}

export {}
declare global {
  interface Window {
    electron: {
      minimize:     () => void
      maximize:     () => void
      close:        () => void
      quit:         () => void
      openExternal: (url: string) => Promise<void>
      getVersion:   () => Promise<string>
    }
  }
}
