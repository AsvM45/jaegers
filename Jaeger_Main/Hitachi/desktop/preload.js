// The dashboard is a normal page. This preload keeps the renderer from touching Node; it only adds
// a way to open the system's microphone settings when access was refused.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("towerDesktop", {
  app: "Wacky Wheels Control Tower",
  openMicSettings: () => ipcRenderer.invoke("open-mic-settings"),
});
