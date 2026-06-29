/**
 * src/main/index.ts — Electron Main Process
 */
import { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell } from 'electron'
import { join } from 'path'
import { spawn, ChildProcess } from 'child_process'
import { existsSync } from 'fs'

declare const MAIN_WINDOW_VITE_DEV_SERVER_URL: string | undefined

const isDev = !app.isPackaged
const API_PORT = 8765
const projectRoot = isDev ? join(app.getAppPath()) : join(process.resourcesPath, '..')

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let fastApiProcess: ChildProcess | null = null

// Electron 단일 인스턴스 잠금
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) { app.quit() }
else {
  app.on('second-instance', () => { mainWindow?.show(); mainWindow?.focus() })
}

declare global { namespace Electron { interface App { isQuitting: boolean } } }
app.isQuitting = false

function startFastApi(): void {
  if (isDev) {
    const venvPython = join(projectRoot, 'venv', 'Scripts', 'python.exe')
    const pythonCmd = existsSync(venvPython) ? venvPython : 'python'
    fastApiProcess = spawn(
      pythonCmd,
      ['-m', 'uvicorn', 'server.api:app', '--host', '127.0.0.1', '--port', String(API_PORT)],
      { cwd: projectRoot, windowsHide: true }
    )
  } else {
    const serverExe = join(process.resourcesPath, 'server_dist', 'api_server.exe')
    if (existsSync(serverExe)) {
      fastApiProcess = spawn(serverExe, [], { windowsHide: true })
    }
  }
  fastApiProcess?.on('error', (e) => console.error('[FastAPI]', e))
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280, height: 800,
    minWidth: 900, minHeight: 600,
    frame: false,
    backgroundColor: '#0f0f0f',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: join(app.getAppPath(), 'resources', 'Agent-J-256.ico'),
    show: false,
  })

  mainWindow.once('ready-to-show', () => mainWindow?.show())

  mainWindow.on('close', (e) => {
    if (!app.isQuitting) { e.preventDefault(); mainWindow?.hide() }
  })

  if (isDev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function createTray(): void {
  const iconFile = 'Agent-J-16.ico'
  const iconPath = isDev
    ? join(app.getAppPath(), 'resources', iconFile)
    : join(process.resourcesPath, iconFile)
  const icon = nativeImage.createFromPath(iconPath)
  tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon)

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Agent J 열기', click: () => mainWindow?.show() },
    { type: 'separator' },
    { label: '종료', click: () => { app.isQuitting = true; app.quit() } }
  ])
  tray.setToolTip('Agent J')
  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => mainWindow?.show())
}

ipcMain.on('window:minimize', () => mainWindow?.minimize())
ipcMain.on('window:maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize()
  else mainWindow?.maximize()
})
ipcMain.on('window:close', () => mainWindow?.hide())
ipcMain.on('window:quit', () => { app.isQuitting = true; app.quit() })

ipcMain.handle('shell:openExternal', (_, url: string) => shell.openExternal(url))
ipcMain.handle('app:getVersion', () => app.getVersion())

app.whenReady().then(() => {
  startFastApi()
  createWindow()
  createTray()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  app.isQuitting = true
  if (fastApiProcess) { fastApiProcess.kill(); fastApiProcess = null }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
