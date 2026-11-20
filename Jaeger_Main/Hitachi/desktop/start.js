// npm start: launch the desktop app. Terminals inside VS Code (and other Electron apps) set
// ELECTRON_RUN_AS_NODE=1, which would make Electron run as plain Node and fail; clear it first.
const { spawn } = require("child_process");
const electron = require("electron"); // in Node, the path to the Electron binary

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
const child = spawn(electron, [__dirname, ...process.argv.slice(2)], { stdio: "inherit", env });
child.on("exit", (code, signal) => process.exit(signal ? 1 : code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
