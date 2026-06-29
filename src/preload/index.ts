import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electron', {
  minimize:      () => ipcRenderer.send('window:minimize'),
  maximize:      () => ipcRenderer.send('window:maximize'),
  close:         () => ipcRenderer.send('window:close'),
  quit:          () => ipcRenderer.send('window:quit'),
  openExternal:  (url: string) => ipcRenderer.invoke('shell:openExternal', url),
  getVersion:    () => ipcRenderer.invoke('app:getVersion'),
})
