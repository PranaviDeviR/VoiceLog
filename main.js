const { app, BrowserWindow, session } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const HOST = "127.0.0.1";
const PORT = 5000;
const APP_URL = `http://${HOST}:${PORT}`;
let pythonProcess = null;
let mainWindow = null;

function isTrustedLocalOrigin(value) {
    try {
        const parsed = new URL(value);
        return parsed.protocol === "http:" &&
            (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") &&
            parsed.port === String(PORT);
    } catch {
        return false;
    }
}

function configureMicrophonePermissions() {
    const appSession = session.defaultSession;

    appSession.setPermissionRequestHandler(
        (webContents, permission, callback, details) => {
            const requestUrl = details?.requestingUrl || webContents.getURL();
            const isAudioRequest =
                !details?.mediaTypes ||
                details.mediaTypes.includes("audio");

            if (
                permission === "media" &&
                isAudioRequest &&
                isTrustedLocalOrigin(requestUrl)
            ) {
                callback(true);
                return;
            }

            callback(false);
        }
    );

    appSession.setPermissionCheckHandler(
        (webContents, permission, requestingOrigin) => {
            if (
                permission === "media" &&
                isTrustedLocalOrigin(requestingOrigin)
            ) {
                return true;
            }

            return false;
        }
    );
}

function isServerReady() {
    return new Promise((resolve) => {
        const request = http.get(`${APP_URL}/health`, (response) => {
            response.resume();
            resolve(response.statusCode === 200);
        });

        request.setTimeout(1000, () => {
            request.destroy();
            resolve(false);
        });

        request.on("error", () => resolve(false));
    });
}

async function waitForServer(maxAttempts = 40) {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        if (pythonProcess && pythonProcess.exitCode !== null) {
            throw new Error(
                `Flask process exited with code ${pythonProcess.exitCode}`
            );
        }

        if (await isServerReady()) {
            return;
        }

        await new Promise((resolve) => setTimeout(resolve, 500));
    }

    throw new Error("Flask did not become ready at " + APP_URL);
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1050,
        height: 780,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true
        }
    });

    mainWindow.loadURL(APP_URL);

    mainWindow.on("closed", () => {
        mainWindow = null;
    });
}

function startBackend() {
    const pythonExecutable = process.env.PYTHON_EXECUTABLE || "python";
    const scriptPath = path.join(__dirname, "VoiceLog.py");

    pythonProcess = spawn(
        pythonExecutable,
        ["-u", scriptPath],
        {
            cwd: __dirname,
            windowsHide: true,
            stdio: ["ignore", "pipe", "pipe"]
        }
    );

    pythonProcess.stdout.on("data", (data) => {
        console.log(`[Flask] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on("data", (data) => {
        console.error(`[Flask] ${data.toString().trim()}`);
    });

    pythonProcess.on("error", (error) => {
        console.error("Could not start Python backend:", error);
    });

    pythonProcess.on("exit", (code) => {
        console.log(`Python backend exited with code ${code}`);
    });
}

app.whenReady().then(async () => {
    configureMicrophonePermissions();
    startBackend();

    try {
        await waitForServer();
        createWindow();
    } catch (error) {
        console.error(error);
        app.quit();
    }
});

app.on("before-quit", () => {
    if (pythonProcess && pythonProcess.exitCode === null) {
        pythonProcess.kill();
    }
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }
});

app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0 && isServerReady()) {
        createWindow();
    }
});
