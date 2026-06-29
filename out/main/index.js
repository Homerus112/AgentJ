"use strict";
const electron = require("electron");
const path = require("path");
const child_process = require("child_process");
const fs = require("fs");
const isDev = !electron.app.isPackaged;
const API_PORT = 8765;
const projectRoot = isDev ? path.join(electron.app.getAppPath()) : path.join(process.resourcesPath, "..");
let mainWindow = null;
let tray = null;
let fastApiProcess = null;
const gotLock = electron.app.requestSingleInstanceLock();
if (!gotLock) {
  electron.app.quit();
} else {
  electron.app.on("second-instance", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}
electron.app.isQuitting = false;
function startFastApi() {
  if (isDev) {
    const venvPython = path.join(projectRoot, "venv", "Scripts", "python.exe");
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : "python";
    fastApiProcess = child_process.spawn(
      pythonCmd,
      ["-m", "uvicorn", "server.api:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
      { cwd: projectRoot, windowsHide: true }
    );
  } else {
    const serverExe = path.join(process.resourcesPath, "server_dist", "api_server.exe");
    if (fs.existsSync(serverExe)) {
      fastApiProcess = child_process.spawn(serverExe, [], { windowsHide: true });
    }
  }
  fastApiProcess?.on("error", (e) => console.error("[FastAPI]", e));
}
function createWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    backgroundColor: "#0f0f0f",
    webPreferences: {
      preload: path.join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false
    },
    icon: path.join(electron.app.getAppPath(), "resources", "Agent-J-256.ico"),
    show: false
  });
  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("close", (e) => {
    if (!electron.app.isQuitting) {
      e.preventDefault();
      mainWindow?.hide();
    }
  });
  if (isDev && process.env["ELECTRON_RENDERER_URL"]) {
    mainWindow.loadURL(process.env["ELECTRON_RENDERER_URL"]);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }
}
function createTray() {
  const iconFile = "Agent-J-16.ico";
  const iconPath = isDev ? path.join(electron.app.getAppPath(), "resources", iconFile) : path.join(process.resourcesPath, iconFile);
  const icon = electron.nativeImage.createFromPath(iconPath);
  tray = new electron.Tray(icon.isEmpty() ? electron.nativeImage.createEmpty() : icon);
  const contextMenu = electron.Menu.buildFromTemplate([
    { label: "Agent J 열기", click: () => mainWindow?.show() },
    { type: "separator" },
    { label: "종료", click: () => {
      electron.app.isQuitting = true;
      electron.app.quit();
    } }
  ]);
  tray.setToolTip("Agent J");
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => mainWindow?.show());
}
electron.ipcMain.on("window:minimize", () => mainWindow?.minimize());
electron.ipcMain.on("window:maximize", () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
electron.ipcMain.on("window:close", () => mainWindow?.hide());
electron.ipcMain.on("window:quit", () => {
  electron.app.isQuitting = true;
  electron.app.quit();
});
electron.ipcMain.handle("shell:openExternal", (_, url) => electron.shell.openExternal(url));
electron.ipcMain.handle("app:getVersion", () => electron.app.getVersion());
electron.app.whenReady().then(() => {
  startFastApi();
  createWindow();
  createTray();
});
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
electron.app.on("before-quit", () => {
  electron.app.isQuitting = true;
  if (fastApiProcess) {
    fastApiProcess.kill();
    fastApiProcess = null;
  }
});
electron.app.on("activate", () => {
  if (electron.BrowserWindow.getAllWindows().length === 0) createWindow();
});
