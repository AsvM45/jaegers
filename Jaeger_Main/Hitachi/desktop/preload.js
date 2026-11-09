// The dashboard is a normal page. This preload keeps the renderer from touching Node.
const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("towerDesktop", { app: "Wacky Wheels Control Tower" });
