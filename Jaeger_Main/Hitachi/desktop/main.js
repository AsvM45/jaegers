// Desktop shell. Starts the Python dashboard on 127.0.0.1 and shows it in a window.
// Quit stops the server. A second launch focuses this window instead of starting another server.

const { app, BrowserWindow, Menu, dialog, ipcMain, session, shell, systemPreferences } = require("electron");
const { spawn, execFileSync } = require("child_process");
const http = require("http");
const net = require("net");
const path = require("path");

const HITACHI = path.resolve(__dirname, "..");
const BOOT = path.join(__dirname, "boot.html");
const HOST = "127.0.0.1";

let serverProc = null;
let mainWindow = null;
let origin = "";

app.setName("Wacky Wheels Control Tower");
app.setAppUserModelId("com.wackywheels.controltower");

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}

function findPython() {
  const tries = [];
  if (process.env.TOWER_PYTHON) tries.push([process.env.TOWER_PYTHON]);
  // macOS and most Linux installs have only python3; Windows has python or the py launcher.
  if (process.platform === "win32") tries.push(["python"], ["py", "-3"], ["python3"]);
  else tries.push(["python3"], ["python"]);
  for (const args of tries) {
    try {
      const out = execFileSync(
        args[0],
        [...args.slice(1), "-c", "import sys; print(sys.executable)"],
        { windowsHide: true, encoding: "utf8", timeout: 15000 },
      );
      const line = out.trim().split(/\r?\n/).filter(Boolean).pop();
      if (line) return line;
    } catch {
      // try the next launcher
    }
  }
  return null;
}

// The same port every launch when it is free: the page's saved Settings (language, theme) are kept
// per address, so a new random port each time would forget them. TOWER_DESKTOP_PORT overrides it.
const PREFERRED_PORT = Number(process.env.TOWER_DESKTOP_PORT) || 47820;

function tryPort(port) {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", reject);
    probe.listen(port, HOST, () => {
      const { port: got } = probe.address();
      probe.close(() => resolve(got));
    });
  });
}

async function freePort() {
  try {
    return await tryPort(PREFERRED_PORT);
  } catch {
    return tryPort(0); // taken (another copy, or another app): any free port
  }
}

function waitForReady(url, child, timeoutMs) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (err) => {
      if (settled) return;
      settled = true;
      if (err) reject(err);
      else resolve();
    };
    const tick = () => {
      if (settled) return;
      if (child.exitCode !== null) {
        finish(new Error(`The dashboard server stopped (exit ${child.exitCode}).`));
        return;
      }
      if (Date.now() - started > timeoutMs) {
        finish(new Error("The dashboard did not answer in time."));
        return;
      }
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode === 200) finish();
        else setTimeout(tick, 250);
      });
      req.setTimeout(2000, () => req.destroy());
      req.on("error", () => setTimeout(tick, 250));
    };
    tick();
  });
}

function stopServer() {
  const child = serverProc;
  serverProc = null;
  if (!child || child.pid == null) return;
  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
    } else {
      child.kill("SIGTERM");
    }
  } catch {
    // already gone
  }
}

function setStatus(text, failed) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const script = `(() => {
    const el = document.getElementById("status");
    const spin = document.getElementById("spin");
    if (el) el.textContent = ${JSON.stringify(text)};
    if (spin && ${failed ? "true" : "false"}) spin.style.display = "none";
  })()`;
  mainWindow.webContents.executeJavaScript(script).catch(() => {});
}

function allowUrl(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (parsed.protocol === "file:") {
    return parsed.pathname.replace(/\\/g, "/").endsWith("/boot.html");
  }
  if (!origin) return false;
  const home = new URL(origin);
  return parsed.protocol === home.protocol && parsed.hostname === home.hostname && parsed.port === home.port;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    backgroundColor: "#070c27",
    title: "Wacky Wheels Control Tower",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (allowUrl(url)) return { action: "allow" };
    shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!allowUrl(url)) event.preventDefault();
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  mainWindow.loadFile(BOOT);
}

async function startServer() {
  const python = findPython();
  if (!python) {
    setStatus("Python was not found. Install Python 3, or set TOWER_PYTHON to python.exe.", true);
    return;
  }
  let port;
  try {
    port = await freePort();
  } catch (err) {
    setStatus(`Could not pick a port: ${err.message}`, true);
    return;
  }
  origin = `http://${HOST}:${port}`;
  const logs = [];
  const child = spawn(python, ["-m", "tower.ui.server", "--port", String(port)], {
    cwd: HITACHI,
    windowsHide: true,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  serverProc = child;
  const keep = (buf) => {
    logs.push(buf.toString());
    if (logs.length > 40) logs.shift();
  };
  child.stdout.on("data", keep);
  child.stderr.on("data", keep);
  child.on("exit", (code) => {
    if (serverProc !== child) return;
    serverProc = null;
    if (!mainWindow || mainWindow.isDestroyed()) return;
    const tail = logs.join("").trim().split(/\r?\n/).slice(-6).join(" ");
    const message = `The dashboard server stopped${tail ? `: ${tail}` : ` (exit ${code}).`}`;
    const show = () => setStatus(message, true);
    if (mainWindow.webContents.getURL().startsWith(origin)) {
      mainWindow.webContents.once("did-finish-load", show);
      mainWindow.loadFile(BOOT).catch(show);
    } else {
      show();
    }
  });
  try {
    await waitForReady(`${origin}/`, child, 45000);
  } catch (err) {
    const tail = logs.join("").trim().split(/\r?\n/).slice(-8).join("\n");
    setStatus(`${err.message}${tail ? " " + tail : ""}`, true);
    stopServer();
    return;
  }
  if (!mainWindow || mainWindow.isDestroyed()) {
    stopServer();
    return;
  }
  await mainWindow.loadURL(`${origin}/`);
  mainWindow.setTitle("Wacky Wheels Control Tower");
}

function buildMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        {
          label: "Reload dashboard",
          accelerator: "CmdOrCtrl+R",
          click: () => {
            if (mainWindow && origin) mainWindow.loadURL(`${origin}/`);
          },
        },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
        { role: "toggleDevTools" },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.on("second-instance", () => {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.focus();
});

// Microphone for voice input: the dashboard (and only the dashboard) may record audio. On macOS
// the app also needs the system's permission, which askForMediaAccess asks for the first time.
const MIC_SETTINGS = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";

async function macMicrophone() {
  if (process.platform !== "darwin") return true;
  const status = systemPreferences.getMediaAccessStatus("microphone");
  if (status === "granted") return true;
  if (status === "not-determined") return systemPreferences.askForMediaAccess("microphone");
  return false; // denied or restricted: only System Settings can change it
}

function allowMicrophone() {
  const fromDashboard = (url) => !!origin && allowUrl(url || "") && !String(url).startsWith("file:");
  session.defaultSession.setPermissionRequestHandler((_contents, permission, callback, details) => {
    const audioOnly = permission === "media" && (details.mediaTypes || []).every((t) => t === "audio");
    if (!audioOnly || !fromDashboard(details.requestingUrl)) return callback(false);
    macMicrophone().then(callback, () => callback(false));
  });
  session.defaultSession.setPermissionCheckHandler((_contents, permission, requestingOrigin) =>
    permission === "media" && fromDashboard(requestingOrigin));
  ipcMain.handle("open-mic-settings", () => {
    if (process.platform === "darwin") return shell.openExternal(MIC_SETTINGS);
    if (process.platform === "win32") return shell.openExternal("ms-settings:privacy-microphone");
    return null;
  });
}

app.whenReady().then(() => {
  if (!gotLock) return;
  allowMicrophone();
  buildMenu();
  createWindow();
  startServer().catch((err) => {
    dialog.showErrorBox("Wacky Wheels Control Tower", err.message);
  });
});

app.on("before-quit", () => {
  stopServer();
});

app.on("window-all-closed", () => {
  stopServer();
  app.quit();
});
