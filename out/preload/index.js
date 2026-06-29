"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electron", {
  minimize: () => electron.ipcRenderer.send("window:minimize"),
  maximize: () => electron.ipcRenderer.send("window:maximize"),
  close: () => electron.ipcRenderer.send("window:close"),
  quit: () => electron.ipcRenderer.send("window:quit"),
  openExternal: (url) => electron.ipcRenderer.invoke("shell:openExternal", url),
  getVersion: () => electron.ipcRenderer.invoke("app:getVersion")
});
